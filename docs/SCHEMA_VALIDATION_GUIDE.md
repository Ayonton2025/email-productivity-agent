# API Schema Validation Guide

This document explains the Pydantic schema validation system and how to apply it across the API.

## Overview

All API endpoints now have **strict input validation** using Pydantic BaseModel schemas defined in `backend/app/api/schemas.py`. This provides:

- ✅ **Type Safety**: FastAPI validates request data types automatically
- ✅ **Input Constraints**: min/max values, length limits, regex patterns
- ✅ **Auto Documentation**: Request/response schemas appear in OpenAPI docs
- ✅ **Error Handling**: Invalid data returns 422 with clear error messages
- ✅ **Serialization**: Automatic JSON conversion with datetime/enum support

## Available Schemas

### Authentication Schemas
- `LoginRequest`: Email + password (min 8 chars)
- `RegisterRequest`: Email + full_name + strong password validation
- `TokenResponse`: access_token, token_type, expires_in

### Email Schemas
- `EmailBase`: subject, body_text, body_html
- `EmailRequest`: EmailBase + recipient
- `EmailResponse`: Complete email object with metadata
- `EmailCategory`: Enum (WORK, PERSONAL, NEWSLETTER, PROMOTIONAL, SOCIAL, OTHER)

### Email Account Schemas
- `EmailAccountRequest`: provider, access_token, refresh_token
- `EmailAccountResponse`: id, email, provider, status, last_sync, total_emails

### Bulk Operations
- `BulkEmailActionRequest`: email_ids list (1-1000 items, unique validation)
- `BulkMarkReadRequest`: Extends BulkEmailActionRequest + is_read flag
- `BulkFlagRequest`: Extends BulkEmailActionRequest + is_flagged flag
- `BulkCategorizeRequest`: Extends BulkEmailActionRequest + category enum
- `BulkDeleteRequest`: Extends BulkEmailActionRequest + soft_delete flag

### Search Schemas
- `SearchRequest`: Simple search with filters
  - query (1-1000 chars)
  - limit (1-500, default 50)
  - offset (default 0)
  - Optional category, is_read, is_flagged filters

- `AdvancedSearchRequest`: Complex search
  - keywords, search_fields, from_address
  - Optional date_from, date_to, has_attachments
  - category, is_unread_only filters

### Sync History
- `SyncHistoryResponse`: Past sync operation details
- `SyncStatsResponse`: Aggregate sync statistics

### Shared Schemas
- `HealthResponse`: Health check status with dependencies
- `ErrorResponse`: Standardized error format (status, code, message, details)
- `PaginatedResponse`: Generic pagination wrapper

## How to Apply Schemas

### Example 1: GET Email Endpoint

**Before** (no validation):
```python
@router.get("/emails/{email_id}")
async def get_email(email_id: int, db: AsyncSession = Depends(get_db)):
    email = await db.get(Email, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email
```

**After** (with validation):
```python
from app.api.schemas import EmailResponse

@router.get("/emails/{email_id}", response_model=EmailResponse)
async def get_email(email_id: int, db: AsyncSession = Depends(get_db)):
    email = await db.get(Email, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email
```

**Key Changes**:
- Added `response_model=EmailResponse` to `@router.get()`
- Response is automatically validated against schema
- OpenAPI docs auto-generated from EmailResponse fields

### Example 2: POST Email Endpoint

**Before**:
```python
@router.post("/emails")
async def create_email(
    subject: str,
    body_text: str,
    recipient: str,
    db: AsyncSession = Depends(get_db)
):
    # No validation - accepts any string
    email = Email(subject=subject, body_text=body_text, recipient=recipient)
    db.add(email)
    await db.commit()
    return email
```

**After**:
```python
from app.api.schemas import EmailRequest, EmailResponse

@router.post("/emails", response_model=EmailResponse)
async def create_email(
    request: EmailRequest,
    db: AsyncSession = Depends(get_db)
):
    # Automatic validation:
    # - subject: 1-1000 chars (enforced by schema)
    # - recipient: Valid email format (enforced by EmailStr)
    # - body_text: Max 100,000 chars
    
    email = Email(
        subject=request.subject,
        body_text=request.body_text,
        recipient=request.recipient
    )
    db.add(email)
    await db.commit()
    return email
```

**Key Changes**:
- Replaced individual parameters with `request: EmailRequest`
- FastAPI automatically validates request body
- Invalid data returns HTTP 422 with validation errors
- Response automatically validates against EmailResponse

### Example 3: Bulk Operations

**Before**:
```python
@router.post("/emails/bulk/mark-read")
async def bulk_mark_read(email_ids: List[int], is_read: bool, db: AsyncSession = Depends(get_db)):
    # No validation - accepts any list size, duplicate IDs
    for email_id in email_ids:
        email = await db.get(Email, email_id)
        if email:
            email.is_read = is_read
    await db.commit()
    return {"updated": len(email_ids)}
```

**After**:
```python
from app.api.schemas import BulkMarkReadRequest, PaginatedResponse

@router.post("/emails/bulk/mark-read")
async def bulk_mark_read(
    request: BulkMarkReadRequest,
    db: AsyncSession = Depends(get_db)
):
    # Automatic validation:
    # - email_ids: 1-1000 items (min_items=1, max_items=1000)
    # - email_ids: No duplicates (validator checks)
    # - is_read: Boolean (type-checked)
    
    for email_id in request.email_ids:
        email = await db.get(Email, email_id)
        if email:
            email.is_read = request.is_read
    await db.commit()
    return {"updated": len(request.email_ids)}
```

**Key Changes**:
- Request object has automatic validation for list size and uniqueness
- Duplicate IDs are caught before database queries
- Schema enforces min 1, max 1000 items

### Example 4: Search with Filters

**Before**:
```python
@router.get("/emails/search")
async def search_emails(
    query: str,
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    # No validation - limit could be negative, category could be invalid
    stmt = select(Email).where(Email.subject.ilike(f"%{query}%"))
    if category:
        stmt = stmt.where(Email.category == category)
    result = await db.execute(stmt.limit(limit).offset(offset))
    return result.scalars().all()
```

**After**:
```python
from app.api.schemas import SearchRequest

@router.post("/emails/search", response_model=PaginatedResponse)
async def search_emails(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    # Automatic validation:
    # - query: 1-1000 chars
    # - limit: 1-500 (catches invalid values)
    # - offset: >= 0 (non-negative)
    # - category: Must be enum value (WORK, PERSONAL, etc.)
    
    stmt = select(Email).where(Email.subject.ilike(f"%{request.query}%"))
    if request.category:
        stmt = stmt.where(Email.category == request.category)
    
    total = len(await db.execute(select(func.count(Email.id)).select_from(Email)))
    result = await db.execute(stmt.limit(request.limit).offset(request.offset))
    emails = result.scalars().all()
    
    return PaginatedResponse(
        data=[EmailResponse.from_orm(e) for e in emails],
        total=total,
        offset=request.offset,
        limit=request.limit,
        has_more=(request.offset + request.limit) < total
    )
```

## Validation Examples

### Example: Invalid Email Address

**Request**:
```bash
POST /api/emails/send
{
  "to": "not-an-email",
  "subject": "Hello",
  "body_text": "Test"
}
```

**Response** (HTTP 422):
```json
{
  "detail": [
    {
      "loc": ["body", "to"],
      "msg": "Invalid email format",
      "type": "value_error.email"
    }
  ]
}
```

### Example: List Too Large

**Request**:
```bash
POST /api/emails/bulk/mark-read
{
  "email_ids": [1, 2, 3, ... 1001 items],
  "is_read": true
}
```

**Response** (HTTP 422):
```json
{
  "detail": [
    {
      "loc": ["body", "email_ids"],
      "msg": "ensure this value has at most 1000 items",
      "type": "value_error.list.max_items"
    }
  ]
}
```

### Example: Invalid Enum Value

**Request**:
```bash
POST /api/emails/bulk/categorize
{
  "email_ids": [1, 2, 3],
  "category": "invalid_category"
}
```

**Response** (HTTP 422):
```json
{
  "detail": [
    {
      "loc": ["body", "category"],
      "msg": "value is not a valid enumeration member; permitted: 'work', 'personal', 'newsletter', 'promotional', 'social', 'other'",
      "type": "type_error.enum"
    }
  ]
}
```

## Custom Validators

### Validating Password Strength

```python
from pydantic import validator

class RegisterRequest(BaseModel):
    password: str = Field(..., min_length=8)
    
    @validator("password")
    def validate_password(cls, v):
        """Ensure password complexity"""
        if not any(c.isupper() for c in v):
            raise ValueError("Must include uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Must include digit")
        if not any(c in "!@#$%^&*" for c in v):
            raise ValueError("Must include special character")
        return v
```

### Validating Unique Items

```python
from pydantic import validator

class BulkEmailActionRequest(BaseModel):
    email_ids: List[int] = Field(..., min_items=1, max_items=1000)
    
    @validator("email_ids")
    def validate_ids(cls, v):
        """Ensure no duplicates"""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate email IDs provided")
        return v
```

## Updating Endpoints - Checklist

When applying schemas to an endpoint:

- [ ] Import required schema(s) from `app.api.schemas`
- [ ] Update function signature to accept request model instead of individual parameters
- [ ] Add `response_model=ResponseSchema` to the route decorator
- [ ] Update function body to access request fields (e.g., `request.subject` instead of `subject`)
- [ ] Return response data (Pydantic will validate and serialize)
- [ ] Test with invalid data to verify error responses
- [ ] Check OpenAPI docs at `/docs` for auto-generated schema documentation

## Endpoints to Update (Priority Order)

### High Priority (Core Features)
1. **Auth Endpoints** (`auth_endpoints.py`)
   - POST /login → LoginRequest
   - POST /register → RegisterRequest
   - POST /token/refresh → (custom schema)

2. **Email Endpoints** (`endpoints.py`, `user_email_endpoints.py`)
   - GET /emails/{id} → response_model=EmailResponse
   - POST /emails → EmailRequest
   - PUT /emails/{id} → EmailRequest
   - DELETE /emails → BulkDeleteRequest

3. **Email Account Endpoints** (`user_email_endpoints.py`)
   - POST /accounts/connect → EmailAccountRequest
   - POST /accounts/test → TestConnectionRequest
   - GET /accounts → response_model=List[EmailAccountResponse]

### Medium Priority (Features)
4. **Bulk Operations** (`email_provider_endpoints.py`)
   - POST /emails/bulk/mark-read → BulkMarkReadRequest
   - POST /emails/bulk/flag → BulkFlagRequest
   - POST /emails/bulk/categorize → BulkCategorizeRequest
   - POST /emails/bulk/delete → BulkDeleteRequest

5. **Search Endpoints** (`endpoints.py`)
   - POST /emails/search → SearchRequest
   - POST /emails/advanced-search → AdvancedSearchRequest

6. **Insights/Agent Endpoints** (`insights_endpoints.py`, `agent_endpoints.py`)
   - Various endpoints with request validation

### Low Priority (Can be Extended Later)
7. **Workflow/Campaign/Billing Endpoints**
   - Existing functionality, lower traffic
   - Can be updated incrementally

## Testing with Schemas

### Using curl:

```bash
# Valid request
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'

# Invalid request (short password)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "short"
  }'
# Returns HTTP 422 with validation error
```

### Using Python client:

```python
from app.api.schemas import LoginRequest

# This will raise ValidationError if data is invalid
request = LoginRequest(
    email="user@example.com",
    password="SecurePass123!"
)
print(f"Validated email: {request.email}")
```

## Benefits

1. **Security**: Prevents invalid/malicious input at the boundary
2. **Documentation**: OpenAPI docs generated from schemas
3. **Consistency**: All endpoints use same validation patterns
4. **Debugging**: Clear error messages for invalid requests
5. **Maintainability**: Type hints and field descriptions in one place
6. **Performance**: Invalid requests rejected before hitting database

## References

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Request Body](https://fastapi.tiangolo.com/tutorial/body/)
- [FastAPI Response Models](https://fastapi.tiangolo.com/tutorial/response_model/)
- [EmailStr Validation](https://docs.pydantic.dev/latest/#use-of-optional-and-typing-union)
