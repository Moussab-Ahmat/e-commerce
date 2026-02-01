"""
Firebase Admin SDK initialization for push notifications.

Firebase is used ONLY for sending push notifications.
All data remains in PostgreSQL.
"""
import os
import logging
import firebase_admin
from firebase_admin import credentials
from django.conf import settings

logger = logging.getLogger(__name__)


def initialize_firebase():
    """
    Initialize Firebase Admin SDK.
    Should be called once at Django startup.
    """
    # Avoid double initialization
    if firebase_admin._apps:
        logger.info('Firebase already initialized')
        return

    credential_path = getattr(
        settings,
        'FIREBASE_CREDENTIALS_PATH',
        os.path.join(settings.BASE_DIR, 'config', 'firebase', 'serviceAccountKey.json')
    )

    if not os.path.exists(credential_path):
        logger.warning(
            f'Firebase credentials not found at {credential_path}. '
            'Push notifications will not work. '
            'Download serviceAccountKey.json from Firebase Console.'
        )
        return

    try:
        cred = credentials.Certificate(credential_path)
        firebase_admin.initialize_app(cred)
        logger.info('Firebase Admin SDK initialized successfully')
    except Exception as e:
        logger.error(f'Failed to initialize Firebase: {e}')
