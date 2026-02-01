"""
Serializers for the reports app.
"""
from rest_framework import serializers
from .models import Invoice, InvoiceSent


class InvoiceSentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceSent
        fields = ['id', 'sent_to', 'sent_at', 'status', 'error_message']


class InvoiceSerializer(serializers.ModelSerializer):
    sends = InvoiceSentSerializer(many=True, read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'pdf_url', 'total_amount', 'created_at', 'sends']

    def get_pdf_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class SendInvoiceSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, help_text='Override recipient email')


class SalesReportSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class DeliveriesReportSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    courier_id = serializers.IntegerField(required=False, allow_null=True)
