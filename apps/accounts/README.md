# Accounts App

Custom User model with phone number authentication, OTP verification, and JWT tokens.

## Features

- Custom User model with phone number (+235 format) as unique identifier
- User roles: CUSTOMER, ADMIN, WAREHOUSE, COURIER
- OTP request/verify endpoints with rate limiting (5 per hour)
- JWT login/refresh requiring OTP verification token
- Mock SMS sending via SMSLog table
- Comprehensive unit tests

## API Endpoints

### OTP Request
```
POST /api/auth/otp/request/
Body: {"phone_number": "+23512345678"}
Response: {"message": "OTP sent successfully", "expires_in": 600}
```

### OTP Verify
```
POST /api/auth/otp/verify/
Body: {"phone_number": "+23512345678", "otp_code": "123456"}
Response: {"message": "OTP verified successfully", "otp_verification_token": "123456", "expires_in": 1800}
```

### Login (requires OTP verification token)
```
POST /api/auth/login/
Body: {
  "phone_number": "+23512345678",
  "password": "password",
  "otp_verification_token": "123456"
}
Response: {"access": "...", "refresh": "...", "user": {...}}
```

### Token Refresh
```
POST /api/auth/token/refresh/
Body: {"refresh": "..."}
Response: {"access": "..."}
```

### User Profile
```
GET /api/auth/profile/
Headers: Authorization: Bearer <access_token>
Response: {"id": 1, "phone_number": "+23512345678", ...}
```

## Rate Limiting

- Maximum 5 OTP requests per phone number per hour
- OTP expires after 10 minutes
- OTP verification token valid for 30 minutes after verification

## Models

- **User**: Custom user model with phone number and roles
- **OTPVerification**: Stores OTP codes with expiry and verification status
- **SMSLog**: Logs all SMS messages (mocked sending)

## Setup

1. Create migrations:
```bash
python manage.py makemigrations accounts
python manage.py migrate
```

2. Create a superuser:
```bash
python manage.py createsuperuser
# Use phone number format: +235XXXXXXXX
```

3. Run tests:
```bash
pytest tests/test_accounts.py -v
```

