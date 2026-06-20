# SecureCommerce — Technical Report

---

## 1. Project Overview

SecureCommerce is a full-stack e-commerce web application built with **Django REST Framework** (backend) and **React.js** (frontend). Its distinguishing feature is the integration of biometric facial recognition as a mandatory authentication step before checkout, layered on top of standard JWT-based authentication, role-based access control, and a trusted-device/security-event audit trail.

---

## 2. System Architecture

```
Browser (React SPA)
        │
        │  HTTP/REST (JSON + JWT Bearer)
        ▼
Django REST Framework API  ─────────────────────────────────────────
  ├── users/          Custom user model, auth, RBAC
  ├── products/       Product & category catalogue
  ├── cart/           Shopping cart
  ├── orders/         Checkout, order management, analytics
  ├── payments/       Mock payment gateway
  ├── facial_auth/    Face enrolment & verification
  └── trust_management/  Trusted devices, security events
        │
        ▼
   PostgreSQL / SQLite
```

The frontend is a React single-page application that communicates with the backend exclusively through Axios (`src/services/api.js`). A persistent sidebar (`Navbar`) and a floating profile avatar (`TopRightProfile`) are rendered at the `App` level; all authenticated pages are wrapped in `ProtectedRoute`.

---

## 3. Technology Stack

| Layer | Technology |
|---|---|
| Backend language | Python 3.10+ |
| Web framework | Django 4.2, Django REST Framework |
| Authentication | `djangorestframework-simplejwt` (JWT) |
| Database | PostgreSQL (SQLite in development) |
| Face recognition | `face_recognition` (dlib) + OpenCV |
| Embedding encryption | `cryptography.fernet` (AES-128) |
| Frontend framework | React 18, React Router v6 |
| UI library | Material UI (MUI) v5 |
| HTTP client | Axios |
| Cross-origin | `django-cors-headers` |
| Config management | `python-decouple` |

---

## 4. Module Breakdown

### 4.1 Users (`users/`)

**Model — `User`**  
Extends `AbstractBaseUser` + `PermissionsMixin`. Key fields:

| Field | Purpose |
|---|---|
| `email` | Primary identifier (unique) |
| `name` | Display name |
| `role` | `customer`, `manager`, `security`, `admin` |
| `face_embedding` | Fernet-encrypted binary blob of the 128-d face vector |
| `is_face_enrolled` | Boolean flag set after successful enrolment |
| `face_verified_at` | Timestamp of last successful face verification; cleared after checkout |

**Serializers**  
- `RegisterSerializer` enforces strong-password rules (min 8 chars, uppercase required, digit required) via `validate_password`.  
- `UserSerializer` marks sensitive/role fields as `read_only` so they cannot be updated through the profile endpoint.

**Views & Permissions**  
All admin-only endpoints (`UserListView`, `AssignRoleView`, `UserDeactivateView`, `UserDeleteView`, `ResetUserPasswordView`) are protected by `IsAdminRole`. Self-modification guards prevent admins from deactivating or deleting their own account.

**RBAC Permission Classes (`users/permissions.py`)**

| Class | Allowed Roles |
|---|---|
| `IsAdminRole` | `admin` |
| `IsManager` | `admin`, `manager` |
| `IsSecurityOfficer` | `admin`, `security` |
| `IsAdminOrProductManager` | `admin`, `manager` |
| `CanViewSecurityEvents` | `admin`, `security` |
| `IsAdminRoleOrReadOnly` | Read: all authenticated; Write: `admin` |

---

### 4.2 Products (`products/`)

Models: `Category`, `Product`, `Review`.  
Products carry `name`, `description`, `price`, `stock`, `image`, `category` (FK to `Category`), and an `is_active` toggle. The `Review` model records a `is_face_verified` flag, allowing the frontend to badge reviews left during a verified session.  
Admin product management (create, update, delete, toggle active) is restricted to `IsAdminOrProductManager`.

---

### 4.3 Cart (`cart/`)

One `Cart` per user (`OneToOneField`). Each `CartItem` links a `Product` with a quantity; duplicate product entries are prevented by `unique_together = ('cart', 'product')`. The `Cart.total` and `CartItem.subtotal` properties compute amounts dynamically without storing redundant data.

---

### 4.4 Orders (`orders/`)

**CheckoutView** is the security-critical path:

1. Checks `face_verified_at` is present and less than **5 minutes** old; otherwise returns `403 Facial verification required`.
2. Opens a database transaction with `@transaction.atomic`.
3. Locks product rows with `select_for_update()` to prevent race-condition overselling.
4. Validates stock for every item before creating any record.
5. Creates `Order` + `OrderItem` records, decrements stock, empties the cart, and **nulls `face_verified_at`** so the token is single-use.

`AdminAnalyticsView` aggregates monthly sales, order-status breakdowns, face-verification rates, payment statistics, and security event counts for the admin dashboard.

---

### 4.5 Payments (`payments/`)

The payment module is an intentionally **mock** gateway, designed to be replaced with a real provider (Stripe, Flutterwave, etc.) with minimal refactoring.

`validate_card()` performs full client-side-equivalent validation server-side:
- Cardholder name (letters, spaces, hyphens, apostrophes only)
- Card number (digits only, 13–19 characters)
- Expiry (MM/YY or MM/YYYY, not expired)
- CVV (3 or 4 digits)

`mock_process_payment()` calls `validate_card` and returns a fake transaction reference (`TXN-<12 hex chars>`). The card number is stored as **last-4 digits only** (`card_last4`) in `gateway_response` — full PAN is never persisted.

`AdminPaymentRefundView` transitions `payment.status` → `'refunded'` and cascades to `order.status` → `'cancelled'`.

---

### 4.6 Facial Authentication (`facial_auth/`)

**Enrolment flow (`EnrollFaceView`)**  
1. Accepts a Base64-encoded image.  
2. Decodes it with OpenCV (`cv2.imdecode`).  
3. Extracts a 128-dimensional face embedding via `face_recognition`.  
4. Encrypts the embedding with Fernet (`AES-128`) and stores it in `user.face_embedding`.  
5. Sets `user.is_face_enrolled = True`.  
6. Logs a `face_enrolled` security event.

**Verification flow (`VerifyFaceView`)**  
1. Checks enrolment status.  
2. Enforces a **lockout** after 5 failed attempts within 30 minutes (returns `429`).  
3. Decodes and embeds the live image.  
4. Compares against the stored (decrypted) embedding using Euclidean distance with a tolerance of `0.5`.  
5. On success: sets `face_verified_at = now()` (consumed by checkout within 5 min).  
6. On failure: logs `face_failed`, returns remaining attempts, and logs `multiple_face_failures` when the threshold is reached.

**Image quality checks (`_check_image_quality`)**  
Before computing embeddings in production, the utility validates:
- Face occupies ≥ 20% of the frame area.
- Face centre within ±30% horizontal / ±35% vertical of the frame.
- Mean pixel brightness ≥ 50 (not too dark).
- Laplacian variance ≥ 60 (not too blurry).

**Debug bypass**  
When `DEBUG=True`, `get_face_embedding` returns a zero-vector and `VerifyFaceView` auto-enrols users without a webcam. This is controlled by a single settings flag and must be `False` in production.

---

### 4.7 Trust Management (`trust_management/`)

**Models**  
- `TrustedDevice`: maps `(user, device_id)` to a friendly name and trust status.  
- `SecurityEvent`: audit log with `event_type`, `ip_address` (extracted respecting `X-Forwarded-For`), `user_agent`, `risk_score`, and `created_at`.

**Risk scoring (`compute_risk_score`)**  
Heuristic based on `face_failed` events in the past 24 hours: each failure adds `0.25`, capped at `1.0`.

**Event types logged**  
`face_enrolled`, `face_verified`, `face_failed`, `login`, `logout`, `suspicious_login`, `multiple_face_failures`.

**`TrustIndicatorsView`**  
Public endpoint returning a JSON object of boolean trust signals used by the frontend Trust Badges component.

---

## 5. Frontend Architecture

### 5.1 Routing (`App.js`)

All pages are declared in a single `<Routes>` block. Pages requiring authentication are wrapped in `ProtectedRoute`, which redirects to `/login` when no token is present. Role-restricted routes (e.g. `/admin`) receive a `roles` prop that `ProtectedRoute` checks against `user.role`.

### 5.2 Auth Context (`contexts/AuthContext.js`)

`AuthProvider` holds the authenticated user object in React state. On mount it attempts to restore the session from `localStorage` via `/users/profile/`. Provides `login`, `logout`, `register`, and `refreshUser` to consumers.

### 5.3 API Layer (`services/api.js`)

Axios instance with two interceptors:
- **Request**: attaches `Authorization: Bearer <token>` from `localStorage`.
- **Response**: on `401`, silently attempts token refresh via `/users/token/refresh/`; on failure clears storage and redirects to `/login`.

### 5.4 Key Pages

| Page | Purpose |
|---|---|
| `Home.js` | Hero, security pipeline diagram, stats, trust badges |
| `Products.js` / `ProductDetail.js` | Product catalogue and detail with add-to-cart |
| `Cart.js` | Cart review |
| `FaceVerification.js` | Webcam capture → enrol or verify |
| `Checkout.js` | Order summary + card payment form (gated on face verification) |
| `PaymentStatus.js` | Post-payment confirmation |
| `Orders.js` | Order history |
| `Profile.js` | Security score, status items, recent security events |
| `SecurityCenter.js` / `SecurityEvents.js` / `TrustedDevices.js` | User-facing security dashboards |
| `AdminDashboard.js` | Tabbed admin panel (Dashboard, Products, Orders, Customers, Payments, Security Center) |

### 5.5 Admin Dashboard (`AdminDashboard.js`)

Tabs are generated dynamically based on `user.role`, ensuring the UI surface area matches backend permissions. Features include:
- Analytics charts (monthly sales bar, orders by status bar)
- Product CRUD with image upload and category assignment
- Order management with status dropdown and order-detail modal
- Customer management: activate/deactivate, reset password, delete
- Payment list with single-click refund
- Security event log with risk-score colouring

---

## 6. Security Controls

| Control | Implementation |
|---|---|
| SQL Injection | Django ORM with parameterised queries throughout |
| XSS | React DOM escaping; `DOMPurify` available for raw HTML |
| CSRF | `CsrfViewMiddleware`; `CSRF_COOKIE_SECURE=True` in production |
| Password hashing | Django PBKDF2-SHA256 (default) |
| Password policy | Min 8 chars, uppercase, digit enforced at registration |
| JWT auth | Access token 30 min; refresh token 7 days with rotation and blacklisting |
| Facial biometrics | Fernet (AES-128 CBC + HMAC) encrypted 128-d embeddings |
| Face lockout | 5 failures / 30 min → `429 Too Many Requests` |
| Checkout gate | `face_verified_at` must be ≤ 5 min old; nulled after use |
| Rate limiting | DRF throttle: 20 req/min (anon), 100 req/min (user) |
| RBAC | Four roles; per-view permission classes enforce least-privilege |
| HTTPS | `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` all `True` when `DEBUG=False` |
| Clickjacking | `X_FRAME_OPTIONS = 'DENY'` |
| Content sniffing | `SECURE_CONTENT_TYPE_NOSNIFF = True` |
| Card data | Full PAN never persisted; only `card_last4` stored |
| IP extraction | Respects `X-Forwarded-For` for proxy deployments |
| Audit trail | Every auth/face event logged with IP, user agent, risk score |

---

## 7. Data Flow — Secure Checkout

```
User selects items → Cart
        │
        ▼
FaceVerification page
  Camera capture → Base64 → POST /api/facial-auth/verify/
  Backend: decrypt stored embedding, compare, set face_verified_at
        │ (verified)
        ▼
Checkout page (React)
  POST /api/orders/checkout/
  Backend: check face_verified_at ≤ 5 min → atomic stock lock → create Order
        │
        ▼
Payment page
  POST /api/payments/<order_id>/initiate/
  Backend: validate card → mock gateway → create Payment, confirm Order
        │
        ▼
PaymentStatus page (confirmation)
```

---

## 8. API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/users/register/` | None | Register new user |
| POST | `/api/users/login/` | None | Obtain JWT pair |
| POST | `/api/users/token/refresh/` | Refresh token | Rotate access token |
| POST | `/api/users/token/blacklist/` | Authenticated | Logout / blacklist refresh |
| GET/PATCH | `/api/users/profile/` | Authenticated | View / update own profile |
| POST | `/api/users/change-password/` | Authenticated | Change password |
| GET | `/api/users/admin/users/` | Admin | List all users |
| PATCH | `/api/users/admin/users/<id>/role/` | Admin | Assign role |
| POST | `/api/users/admin/users/<id>/deactivate/` | Admin | Toggle active status |
| DELETE | `/api/users/admin/users/<id>/delete/` | Admin | Permanently delete user |
| POST | `/api/users/admin/users/<id>/reset-password/` | Admin | Reset user password |
| GET | `/api/products/` | None | List active products |
| GET | `/api/products/<id>/` | None | Product detail |
| GET/POST/PATCH/DELETE | `/api/products/admin/` | Admin/Manager | Product management |
| GET/POST | `/api/cart/` | Authenticated | View / add to cart |
| PATCH/DELETE | `/api/cart/<id>/` | Authenticated | Update / remove cart item |
| GET | `/api/orders/` | Authenticated | Own order history |
| POST | `/api/orders/checkout/` | Authenticated + face verified | Place order |
| GET | `/api/orders/admin/` | Admin/Manager | All orders |
| PATCH | `/api/orders/admin/<id>/status/` | Admin/Manager | Update order status |
| GET | `/api/orders/admin/analytics/` | Admin/Manager/Security | Aggregated analytics |
| POST | `/api/payments/<order_id>/initiate/` | Authenticated | Process payment |
| GET | `/api/payments/<order_id>/status/` | Authenticated | Payment status |
| GET | `/api/payments/admin/` | Admin/Manager/Security | All payments |
| POST | `/api/payments/admin/<id>/refund/` | Admin/Manager | Refund payment |
| POST | `/api/facial-auth/enroll/` | Authenticated | Enrol face |
| POST | `/api/facial-auth/verify/` | Authenticated | Verify face |
| GET/POST | `/api/trust/devices/` | Authenticated | Trusted devices |
| DELETE | `/api/trust/devices/<id>/` | Authenticated | Remove trusted device |
| GET | `/api/trust/events/` | Authenticated (full list: Admin/Security) | Security events |
| GET | `/api/trust/indicators/` | None | Trust badge data |

---

## 9. Limitations and Recommendations

### 9.1 Debug Bypass Must Be Disabled in Production
`get_face_embedding` returns a zero-vector and `VerifyFaceView` auto-enrols when `DEBUG=True`. This completely bypasses biometric security. **Set `DJANGO_DEBUG=False` and verify before any deployment.**

### 9.2 Single Fernet Key — No Key Rotation
All face embeddings are encrypted with one static `FERNET_KEY`. If this key is rotated, all existing embeddings become unreadable and every user must re-enrol. A `MultiFernet` key-chain should be implemented for zero-downtime rotation.

### 9.3 Mock Payment Gateway
The payment module simulates approvals and declines locally. It must be replaced with a PCI-DSS compliant provider (Stripe, etc.) before handling real cards.

### 9.4 CORS Locked to `localhost:3000`
`CORS_ALLOWED_ORIGINS` only allows the local dev origin. This must be updated with the production frontend URL before deployment.

### 9.5 No Email Verification
Users can register and transact without verifying their email address. An email-confirmation step should be added for production.

### 9.6 Password Reset Exposed via `window.prompt`
The admin "Reset Password" flow uses a browser `prompt()` dialog, which means the plaintext password is visible in the browser UI. This should use a proper form dialog.

### 9.7 Liveness Detection Not Implemented
The face verification accepts a static photo. A real deployment should incorporate liveness detection (e.g. blink challenge, depth map) to prevent spoofing with printed photos.

### 9.8 `AdminPaymentListView` / `AdminPaymentRefundView` Use Manual Role Check
These two views check `request.user.role` inline rather than using a named permission class, which is inconsistent with the rest of the codebase and harder to audit.

---

## 10. Setup Summary

```bash
# 1. Configure environment
cp .env.example .env          # fill DB credentials, SECRET_KEY, FERNET_KEY

# 2. Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser

# 3. Frontend
cd frontend && npm install

# 4. Run both servers
bash run.sh
# or separately:
#   source venv/bin/activate && python manage.py runserver
#   cd frontend && npm start
```

Default URLs:
- Backend API: `http://localhost:8000/api/`
- Frontend: `http://localhost:3000`
- Django admin: `http://localhost:8000/admin/`
