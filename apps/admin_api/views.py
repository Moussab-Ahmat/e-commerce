"""
Admin API viewsets for managing categories, couriers, orders, products, and vendors.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .permissions import IsAdmin
from .serializers import (
    AdminCategorySerializer,
    AdminCourierSerializer,
    AdminCourierCreateSerializer,
    AdminCourierStatsSerializer,
    AdminOrderSerializer,
    AdminAssignCourierSerializer,
    AdminProductSerializer,
    AdminProductCreateSerializer,
    AdminStockUpdateSerializer,
    AdminVendorSerializer
)
from apps.catalog.models import Category, Product
from apps.accounts.models import User
from apps.deliveries.models import DeliveryAgent, Delivery, DeliveryStatus
from apps.orders.models import Order
from apps.vendors.models import Shop


# ============ CATEGORY VIEWSET ============

class AdminCategoryViewSet(viewsets.ModelViewSet):
    """Admin category management viewset."""
    queryset = Category.objects.all().annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    )
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def destroy(self, request, *args, **kwargs):
        """
        Prevent deletion if products exist in this category.
        """
        category = self.get_object()
        if category.products.exists():
            return Response(
                {'error': 'Cannot delete category with existing products'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


# ============ COURIER VIEWSET ============

class AdminCourierViewSet(viewsets.ModelViewSet):
    """Admin courier management viewset."""
    queryset = User.objects.filter(role='COURIER').select_related('delivery_agent')
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['is_active']
    search_fields = ['email', 'phone_number', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'first_name']
    ordering = ['-date_joined']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return AdminCourierCreateSerializer
        return AdminCourierSerializer

    @action(detail=True, methods=['PATCH'])
    def toggle_active(self, request, pk=None):
        """Toggle courier active status."""
        courier = self.get_object()
        courier.is_active = not courier.is_active
        courier.save(update_fields=['is_active'])
        serializer = self.get_serializer(courier)
        return Response(serializer.data)

    @action(detail=True, methods=['GET'])
    def stats(self, request, pk=None):
        """Get detailed courier statistics."""
        courier = self.get_object()

        try:
            deliveries = Delivery.objects.filter(agent__user=courier)
            total = deliveries.count()
            completed = deliveries.filter(status=DeliveryStatus.COMPLETED).count()
            in_progress = deliveries.filter(
                status__in=[DeliveryStatus.ASSIGNED, DeliveryStatus.IN_TRANSIT]
            ).count()
            failed = deliveries.filter(status=DeliveryStatus.FAILED).count()

            success_rate = (completed / total * 100) if total > 0 else 0

            # Calculate average delivery time for completed deliveries
            completed_deliveries = deliveries.filter(
                status=DeliveryStatus.COMPLETED,
                completed_at__isnull=False,
                assigned_at__isnull=False
            )

            avg_time = 0
            if completed_deliveries.exists():
                total_minutes = sum([
                    (d.completed_at - d.assigned_at).total_seconds() / 60
                    for d in completed_deliveries
                ])
                avg_time = int(total_minutes / completed_deliveries.count())

            stats_data = {
                'total_deliveries': total,
                'completed': completed,
                'in_progress': in_progress,
                'failed': failed,
                'success_rate': round(success_rate, 2),
                'avg_delivery_time': avg_time
            }

            serializer = AdminCourierStatsSerializer(stats_data)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['GET'])
    def available(self, request):
        """Get list of available couriers (active with no current deliveries)."""
        available_couriers = User.objects.filter(
            role='COURIER',
            is_active=True
        ).exclude(
            delivery_agent__deliveries__status__in=[
                DeliveryStatus.ASSIGNED,
                DeliveryStatus.IN_TRANSIT
            ]
        ).distinct()

        serializer = self.get_serializer(available_couriers, many=True)
        return Response(serializer.data)


# ============ ORDER VIEWSET ============

class AdminOrderViewSet(viewsets.ModelViewSet):
    """Admin order management viewset."""
    queryset = Order.objects.all().select_related(
        'user', 'courier', 'delivery_zone'
    ).prefetch_related('items')
    serializer_class = AdminOrderSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['status', 'courier']
    search_fields = ['order_number', 'user__email', 'user__phone_number']
    ordering_fields = ['created_at', 'total', 'status']
    ordering = ['-created_at']

    @action(detail=True, methods=['POST'])
    def assign_courier(self, request, pk=None):
        """Assign courier to order."""
        order = self.get_object()
        serializer = AdminAssignCourierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        courier = User.objects.get(id=serializer.validated_data['courier_id'])
        estimated_minutes = serializer.validated_data.get('estimated_minutes', 30)

        try:
            # Get courier's delivery agent
            delivery_agent = courier.delivery_agent

            # Assign courier to order
            order.courier = courier
            order.estimated_minutes = estimated_minutes
            order.save(update_fields=['courier', 'estimated_minutes'])

            # Create or update Delivery object
            delivery, created = Delivery.objects.update_or_create(
                order=order,
                defaults={
                    'agent': delivery_agent,
                    'status': DeliveryStatus.ASSIGNED,
                    'assigned_at': timezone.now(),
                    'estimated_delivery_date': timezone.now() + timedelta(minutes=estimated_minutes),
                    # Copy delivery address from order
                    'delivery_address_line1': order.delivery_address_line1 or '',
                    'delivery_address_line2': order.delivery_address_line2 or '',
                    'delivery_city': order.delivery_city or '',
                    'delivery_region': order.delivery_region or '',
                    'delivery_postal_code': order.delivery_postal_code or '',
                    'delivery_phone': order.delivery_phone or order.user.phone_number or '',
                    'zone': order.delivery_zone,
                    'fee': order.delivery_fee or 0,
                }
            )

            # Generate delivery number if newly created
            if created:
                delivery.delivery_number = f"DEL-{order.order_number}-{delivery.id}"
                delivery.save(update_fields=['delivery_number'])

            return Response({
                'message': 'Courier assigned successfully',
                'order': AdminOrderSerializer(order).data,
                'delivery_id': delivery.id,
                'delivery_number': delivery.delivery_number
            })
        except DeliveryAgent.DoesNotExist:
            return Response(
                {'error': 'This user is not registered as a delivery agent'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['POST'])
    def unassign_courier(self, request, pk=None):
        """Unassign courier from order."""
        order = self.get_object()

        if not order.courier:
            return Response(
                {'error': 'No courier assigned to this order'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete the Delivery object if it exists
        try:
            delivery = order.delivery
            delivery.delete()
        except Delivery.DoesNotExist:
            pass  # No delivery to delete

        order.courier = None
        order.save(update_fields=['courier'])

        return Response({
            'message': 'Courier unassigned successfully',
            'order': AdminOrderSerializer(order).data
        })


# ============ PRODUCT VIEWSET ============

class AdminProductViewSet(viewsets.ModelViewSet):
    """Admin product management viewset."""
    queryset = Product.objects.all().select_related('category', 'shop')
    serializer_class = AdminProductSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['category', 'shop', 'is_active', 'is_featured', 'is_on_sale', 'is_published']
    search_fields = ['name', 'sku', 'description']

    @action(detail=False, methods=['POST'], parser_classes=[MultiPartParser, FormParser])
    def upload_image(self, request):
        """Upload a single product image."""
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        image_file = request.FILES['image']

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Upload attempt - filename: {image_file.name}, content_type: {image_file.content_type}, size: {image_file.size}")

        # Validate file size (max 5MB)
        if image_file.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'Image size must be less than 5MB'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file type by content_type OR extension
        allowed_content_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'application/octet-stream']
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']

        # Get file extension
        filename = image_file.name.lower() if image_file.name else ''
        file_ext = '.' + filename.split('.')[-1] if '.' in filename else ''

        content_type_ok = image_file.content_type in allowed_content_types
        extension_ok = file_ext in allowed_extensions

        logger.info(f"Validation - content_type_ok: {content_type_ok}, extension_ok: {extension_ok}, ext: {file_ext}")

        if not (content_type_ok or extension_ok):
            return Response(
                {'error': f'Only JPEG, PNG, and WebP images are allowed. Got content_type: {image_file.content_type}, extension: {file_ext}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create temporary product image without product (will be linked later)
            from apps.catalog.models import ProductImage
            from django.core.files.uploadedfile import InMemoryUploadedFile
            from PIL import Image as PILImage
            from io import BytesIO
            import uuid

            # Open image with PIL to detect real format
            img = PILImage.open(image_file)
            real_format = img.format or 'JPEG'  # Default to JPEG if format not detected

            logger.info(f"PIL detected format: {real_format}, mode: {img.mode}")

            # Map PIL format to file extension
            format_to_ext = {
                'JPEG': 'jpg',
                'JPG': 'jpg',
                'PNG': 'png',
                'WEBP': 'webp',
                'GIF': 'gif',
            }
            ext = format_to_ext.get(real_format.upper(), 'jpg')

            # Generate unique filename with correct extension
            filename = f"{uuid.uuid4()}.{ext}"

            # Convert RGBA to RGB for JPEG (PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparent images
                background = PILImage.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # Create thumbnail (400x400)
            thumb_img = img.copy()
            thumb_img.thumbnail((400, 400), PILImage.Resampling.LANCZOS)

            # Save thumbnail to BytesIO as JPEG (smaller file size)
            thumb_io = BytesIO()
            thumb_img.save(thumb_io, format='JPEG', quality=85)
            thumb_io.seek(0)

            # Create thumbnail filename (always .jpg since we save as JPEG)
            thumb_filename = f"thumb_{uuid.uuid4()}.jpg"

            # Create InMemoryUploadedFile for thumbnail
            thumbnail_file = InMemoryUploadedFile(
                thumb_io, None, thumb_filename,
                'image/jpeg', thumb_io.getbuffer().nbytes, None
            )

            # Save files directly (they will be saved in MEDIA_ROOT)
            from django.core.files.storage import default_storage

            # Reset the file pointer for original image
            image_file.seek(0)

            # Save original image
            original_full_path = f'products/original/{filename}'
            default_storage.save(original_full_path, image_file)

            # Save thumbnail
            thumbnail_full_path = f'products/thumbnails/{thumb_filename}'
            default_storage.save(thumbnail_full_path, thumbnail_file)

            # Build absolute URLs for preview
            original_url = request.build_absolute_uri(default_storage.url(original_full_path))
            thumbnail_url = request.build_absolute_uri(default_storage.url(thumbnail_full_path))

            return Response({
                'original': original_url,
                'thumbnail': thumbnail_url,
                # Return the full paths for ProductImage creation
                'original_path': original_full_path,
                'thumbnail_path': thumbnail_full_path,
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to upload image: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    ordering_fields = ['created_at', 'price', 'stock_quantity']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return AdminProductCreateSerializer
        return AdminProductSerializer

    def create(self, request, *args, **kwargs):
        """Create a new product with validation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        # Handle uploaded images
        uploaded_images = request.data.get('uploaded_images', [])
        if uploaded_images:
            from apps.catalog.models import ProductImage

            for idx, image_data in enumerate(uploaded_images):
                # image_data should contain original_path and thumbnail_path
                if isinstance(image_data, dict):
                    original_path = image_data.get('original_path')
                    thumbnail_path = image_data.get('thumbnail_path')

                    if original_path and thumbnail_path:
                        # Create ProductImage and assign the path directly to the field
                        product_image = ProductImage(
                            product=product,
                            is_primary=(idx == 0)
                        )
                        # Assign the path directly using .name attribute
                        product_image.original.name = original_path
                        product_image.thumbnail.name = thumbnail_path
                        product_image.save()

        # Return full product details using the read serializer
        read_serializer = AdminProductSerializer(
            product,
            context={'request': request}
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a product with validation.
        Prevent deletion if the product has pending/confirmed orders.
        """
        product = self.get_object()

        # Check for active order items referencing this product
        from apps.orders.models import OrderItem
        active_order_items = OrderItem.objects.filter(
            product=product,
            order__status__in=[
                'PENDING_CONFIRMATION', 'CONFIRMED', 'PICKING',
                'PACKED', 'READY_FOR_DELIVERY', 'OUT_FOR_DELIVERY'
            ]
        )
        if active_order_items.exists():
            return Response(
                {'error': 'Cannot delete product with active orders. '
                          'Deactivate it instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['PATCH'])
    def stock(self, request, pk=None):
        """Update product stock."""
        product = self.get_object()
        serializer = AdminStockUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        operation = serializer.validated_data['operation']
        quantity = serializer.validated_data['stock_quantity']

        if operation == 'set':
            product.stock_quantity = quantity
        elif operation == 'add':
            product.stock_quantity += quantity
        elif operation == 'subtract':
            product.stock_quantity = max(0, product.stock_quantity - quantity)

        product.save(update_fields=['stock_quantity'])

        return Response({
            'message': 'Stock updated successfully',
            'product': AdminProductSerializer(
                product,
                context={'request': request}
            ).data
        })

    @action(detail=True, methods=['PATCH'])
    def toggle_sale(self, request, pk=None):
        """Toggle product sale status.

        When turning ON, accepts optional body params:
        - sale_price: int (will be set if provided)
        - sale_start_date: datetime string (optional)
        - sale_end_date: datetime string (optional)
        """
        product = self.get_object()

        if not product.is_on_sale:
            # Turning on sale - accept sale_price from request body
            incoming_price = request.data.get('sale_price')
            if incoming_price is not None:
                try:
                    incoming_price = int(incoming_price)
                except (ValueError, TypeError):
                    return Response(
                        {'error': 'Prix promotionnel invalide.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                product.sale_price = incoming_price

            # Also accept optional dates
            if 'sale_start_date' in request.data:
                product.sale_start_date = request.data['sale_start_date'] or None
            if 'sale_end_date' in request.data:
                product.sale_end_date = request.data['sale_end_date'] or None

            # Validate sale_price exists
            if not product.sale_price:
                return Response(
                    {'error': 'Impossible d\'activer la promo sans prix promotionnel.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if product.sale_price >= product.price:
                return Response(
                    {'error': 'Le prix promo doit etre inferieur au prix normal.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        update_fields = ['is_on_sale', 'updated_at']
        if not product.is_on_sale:
            # Turning ON - also save sale_price and dates
            update_fields.extend(['sale_price', 'sale_start_date', 'sale_end_date'])

        product.is_on_sale = not product.is_on_sale
        product.save(update_fields=update_fields)

        serializer = AdminProductSerializer(product, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['PATCH'])
    def toggle_published(self, request, pk=None):
        """Toggle product published status."""
        product = self.get_object()
        product.is_published = not product.is_published
        product.save(update_fields=['is_published', 'updated_at'])

        serializer = AdminProductSerializer(product, context={'request': request})
        return Response(serializer.data)


# ============ VENDOR VIEWSET ============

class AdminVendorViewSet(viewsets.ModelViewSet):
    """Admin vendor/shop management viewset."""
    queryset = Shop.objects.all().select_related('vendor').annotate(
        products_count=Count('products')
    )
    serializer_class = AdminVendorSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['status', 'is_verified']
    search_fields = ['name', 'vendor__email', 'business_license']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    @action(detail=True, methods=['PATCH'])
    def approve(self, request, pk=None):
        """Approve vendor shop."""
        shop = self.get_object()
        shop.activate(request.user)
        serializer = self.get_serializer(shop)
        return Response(serializer.data)

    @action(detail=True, methods=['PATCH'])
    def deactivate(self, request, pk=None):
        """Deactivate vendor shop."""
        shop = self.get_object()
        shop.status = Shop.Status.INACTIVE
        shop.save(update_fields=['status'])
        serializer = self.get_serializer(shop)
        return Response(serializer.data)


# ============ ANALYTICS VIEWSET ============

class AdminAnalyticsViewSet(viewsets.ViewSet):
    """Admin analytics dashboard viewset."""
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(detail=False, methods=['GET'])
    def dashboard(self, request):
        """
        Get comprehensive analytics dashboard data.

        Query params:
            - period: number of days (7, 30, 90, 365). Default: 30
        """
        from django.db.models import Sum, Avg, F
        from django.db.models.functions import TruncDate, ExtractWeekDay
        from collections import defaultdict
        import calendar

        # Get period from query params
        period = int(request.query_params.get('period', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=period)
        prev_start_date = start_date - timedelta(days=period)

        # ============ SUMMARY STATS ============

        # Current period orders
        current_orders = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).exclude(status__in=['CANCELLED', 'REFUNDED'])

        # Previous period orders (for comparison)
        prev_orders = Order.objects.filter(
            created_at__gte=prev_start_date,
            created_at__lt=start_date
        ).exclude(status__in=['CANCELLED', 'REFUNDED'])

        # Total revenue
        current_revenue = current_orders.aggregate(
            total=Sum('total')
        )['total'] or 0

        prev_revenue = prev_orders.aggregate(
            total=Sum('total')
        )['total'] or 0

        # Calculate evolution percentage
        evolution_revenue = 0
        if prev_revenue > 0:
            evolution_revenue = round(
                ((current_revenue - prev_revenue) / prev_revenue) * 100, 1
            )

        # Order count
        current_order_count = current_orders.count()
        prev_order_count = prev_orders.count()

        evolution_orders = 0
        if prev_order_count > 0:
            evolution_orders = round(
                ((current_order_count - prev_order_count) / prev_order_count) * 100, 1
            )

        # Active deliveries (in progress)
        active_delivery_statuses = [
            DeliveryStatus.ASSIGNED,
            DeliveryStatus.PICKED_UP,
            DeliveryStatus.IN_TRANSIT,
        ]
        active_deliveries = Delivery.objects.filter(
            status__in=active_delivery_statuses
        ).count()

        # Active couriers
        active_couriers = DeliveryAgent.objects.filter(
            is_active=True
        ).count()

        summary = {
            'total_revenue': current_revenue,
            'total_orders': current_order_count,
            'active_deliveries': active_deliveries,
            'active_couriers': active_couriers,
            'evolution_revenue': evolution_revenue,
            'evolution_orders': evolution_orders,
        }

        # ============ DAILY SALES ============

        daily_sales_qs = current_orders.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            amount=Sum('total')
        ).order_by('date')

        daily_sales = [
            {
                'date': item['date'].strftime('%Y-%m-%d'),
                'amount': item['amount'] or 0
            }
            for item in daily_sales_qs
        ]

        # ============ TOP PRODUCTS ============

        from apps.orders.models import OrderItem

        top_products_qs = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            order__created_at__lte=end_date
        ).exclude(
            order__status__in=['CANCELLED', 'REFUNDED']
        ).values(
            'product__name'
        ).annotate(
            quantity=Sum('quantity'),
            revenue=Sum('total_price')
        ).order_by('-quantity')[:5]

        top_products = [
            {
                'name': item['product__name'],
                'quantity': item['quantity'],
                'revenue': item['revenue'] or 0
            }
            for item in top_products_qs
        ]

        # ============ DELIVERY STATS ============

        all_deliveries = Delivery.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        total_deliveries = all_deliveries.count()

        delivery_stats_qs = all_deliveries.values('status').annotate(
            count=Count('id')
        ).order_by('status')

        status_labels = {
            DeliveryStatus.PENDING: 'En attente',
            DeliveryStatus.ASSIGNED: 'Assignée',
            DeliveryStatus.PICKED_UP: 'Récupérée',
            DeliveryStatus.IN_TRANSIT: 'En cours',
            DeliveryStatus.DELIVERED: 'Livrée',
            DeliveryStatus.COMPLETED: 'Complétée',
            DeliveryStatus.FAILED: 'Échouée',
            DeliveryStatus.CANCELLED: 'Annulée',
            DeliveryStatus.RETURNED: 'Retournée',
        }

        delivery_stats = []
        for item in delivery_stats_qs:
            percentage = round(
                (item['count'] / total_deliveries * 100), 1
            ) if total_deliveries > 0 else 0
            delivery_stats.append({
                'status': status_labels.get(item['status'], item['status']),
                'status_code': item['status'],
                'count': item['count'],
                'percentage': percentage
            })

        # ============ CATEGORY REVENUE ============

        category_revenue_qs = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            order__created_at__lte=end_date
        ).exclude(
            order__status__in=['CANCELLED', 'REFUNDED']
        ).values(
            category_name=F('product__category__name')
        ).annotate(
            revenue=Sum('total_price')
        ).order_by('-revenue')

        category_revenue = [
            {
                'category': item['category_name'] or 'Non catégorisé',
                'revenue': item['revenue'] or 0
            }
            for item in category_revenue_qs
        ]

        # ============ WEEKDAY ORDERS ============

        weekday_qs = current_orders.annotate(
            weekday=ExtractWeekDay('created_at')
        ).values('weekday').annotate(
            count=Count('id')
        ).order_by('weekday')

        # Django: 1=Sunday, 2=Monday, ..., 7=Saturday
        # We want: 0=Monday, 1=Tuesday, ..., 6=Sunday
        weekday_names = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']
        weekday_map = {1: 6, 2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5}  # Django to 0=Mon

        weekday_counts = {i: 0 for i in range(7)}
        for item in weekday_qs:
            mapped_day = weekday_map.get(item['weekday'], 0)
            weekday_counts[mapped_day] = item['count']

        weekday_orders = [
            {
                'weekday': weekday_names[i + 1] if i < 6 else weekday_names[0],
                'weekday_index': i,
                'count': weekday_counts[i]
            }
            for i in range(7)
        ]

        # Reorder to start with Monday
        weekday_orders_ordered = weekday_orders[0:7]  # Already 0=Mon in weekday_map

        # Calculate average for reference line
        total_weekday_orders = sum(item['count'] for item in weekday_orders)
        avg_daily_orders = round(total_weekday_orders / 7, 1) if total_weekday_orders > 0 else 0

        return Response({
            'summary': summary,
            'daily_sales': daily_sales,
            'top_products': top_products,
            'delivery_stats': delivery_stats,
            'category_revenue': category_revenue,
            'weekday_orders': weekday_orders_ordered,
            'weekday_average': avg_daily_orders,
            'period': period,
        })
