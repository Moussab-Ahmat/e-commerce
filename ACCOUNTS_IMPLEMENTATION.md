# Accounts App Implementation Summary

## ✅ Implementation Complete

### Custom User Model
- **File**: `apps/accounts/models.py`
- Phone number (+235XXXXXXXX) as unique identifier
- Roles: CUSTOMER, ADMIN, WAREHOUSE, COURIER
- OTP verification status tracking
- Custom UserManager for user/superuser creation

### OTP System
- **OTP Request Endpoint**: `/api/auth/otp/request/`
  - Rate limiting: 5 requests per hour per phone number
  - 10-minute expiry
  - Mock SMS logging to SMSLog table
  
- **OTP Verify Endpoint**: `/api/auth/otp/verify/`
  - Validates OTP code
  - Returns verification token (valid 30 minutes)
  - Marks OTP as verified

### JWT Authentication
- **Login Endpoint**: `/api/auth/login/`
  - Requires phone number, password, and OTP verification token
  - Returns JWT access and refresh tokens
  - Marks user as verified
  - Marks OTP token as used

- **Token Refresh**: `/api/auth/token/refresh/`
  - Standard JWT refresh endpoint

### Models Created
1. **User** (`accounts.User`)
   - Custom user model with phone number authentication
   - Role-based access control
   - OTP verification status

2. **OTPVerification**
   - Stores OTP codes
   - Tracks verification and usage status
   - Expiry tracking

3. **SMSLog**
   - Mock SMS sending log
   - Tracks SMS status and errors
   - Stores OTP codes for debugging

### Admin Integration
- **File**: `apps/accounts/admin.py`
- User admin with role management
- OTP verification admin
- SMS log admin

### Unit Tests
- **File**: `tests/test_accounts.py`
- **TestOTPFlow**: OTP request, verification, rate limiting, expiry
- **TestJWTAuth**: Login flow, token refresh, authenticated endpoints
- **TestUserModel**: User creation, roles, validation
- **TestOTPService**: Service methods, rate limiting

### Configuration Updates
- `config/settings/base.py`: Added `AUTH_USER_MODEL = 'accounts.User'`
- `config/urls.py`: Added accounts app URLs
- `INSTALLED_APPS`: Added `apps.accounts`

## Setup Instructions

### 1. Create Migrations
```bash
python manage.py makemigrations accounts
python manage.py migrate
```

### 2. Create Superuser
```bash
python manage.py createsuperuser
# Use phone number format: +235XXXXXXXX
```

### 3. Run Tests
```bash
pytest tests/test_accounts.py -v
pytest tests/test_accounts.py::TestOTPFlow -v
pytest tests/test_accounts.py::TestJWTAuth -v
```

## API Flow Example

1. **Request OTP**:
```bash
POST /api/auth/otp/request/
{"phone_number": "+23512345678"}
```

2. **Verify OTP**:
```bash
POST /api/auth/otp/verify/
{"phone_number": "+23512345678", "otp_code": "123456"}
# Returns: {"otp_verification_token": "123456", ...}
```

3. **Login**:
```bash
POST /api/auth/login/
{
  "phone_number": "+23512345678",
  "password": "password",
  "otp_verification_token": "123456"
}
# Returns: {"access": "...", "refresh": "...", "user": {...}}
```

4. **Use Access Token**:
```bash
GET /api/auth/profile/
Headers: Authorization: Bearer <access_token>
```

## Rate Limiting Details

- **Cache-based**: Uses Django cache (Redis recommended)
- **Limit**: 5 OTP requests per phone number per hour
- **Window**: 1 hour rolling window
- **Response**: 429 Too Many Requests when exceeded

## Security Features

- Phone number validation (Chad format: +235XXXXXXXX)
- OTP expiry (10 minutes)
- OTP verification token expiry (30 minutes)
- Rate limiting on OTP requests
- JWT token rotation
- Password hashing (Django default)
- OTP single-use enforcement

## Files Created/Modified

### Created
- `apps/accounts/models.py`
- `apps/accounts/serializers.py`
- `apps/accounts/services.py`
- `apps/accounts/views.py`
- `apps/accounts/urls.py`
- `apps/accounts/admin.py`
- `apps/accounts/apps.py`
- `apps/accounts/__init__.py`
- `apps/accounts/README.md`
- `tests/test_accounts.py`

### Modified
- `config/settings/base.py` (AUTH_USER_MODEL, INSTALLED_APPS)
- `config/urls.py` (added accounts URLs)
- `tests/conftest.py` (added cache clearing fixture)

## Test Coverage

- ✅ OTP request success
- ✅ OTP request rate limiting
- ✅ OTP request invalid phone format
- ✅ OTP verification success
- ✅ OTP verification invalid code
- ✅ OTP verification expired
- ✅ OTP verification already used
- ✅ Login without OTP token (fails)
- ✅ Login with OTP token (success)
- ✅ Login invalid credentials
- ✅ Login expired OTP token
- ✅ Token refresh
- ✅ Authenticated endpoint access
- ✅ User model creation
- ✅ User roles
- ✅ Phone number validation
- ✅ OTP service methods
- ✅ Rate limit checking

All tests pass with pytest-django configuration.

