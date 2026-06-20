# SecureCommerce - Secure E-Commerce Web Application

A Django + React e-commerce application featuring facial recognition authentication, trusted computing principles, and payment API integration.

## Tech Stack
- **Backend**: Python, Django, Django REST Framework, PostgreSQL, JWT
- **Frontend**: React.js, Material UI, Axios, React Router
- **Security**: Facial Recognition, AES Encryption, CSRF, XSS Protection, Rate Limiting

---

## Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- A webcam (for facial recognition)

---

## Setup

### 1. Database
```bash
sudo -u postgres psql
CREATE DATABASE ecommerce_db;
CREATE USER postgres WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE ecommerce_db TO postgres;
\q
```

### 2. Backend
```bash
# Generate a Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Edit .env with your DB credentials and the Fernet key
nano .env

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Install face recognition (requires cmake + dlib)
pip install face-recognition opencv-python-headless
```

### 3. Frontend
```bash
cd frontend
npm install
```

### 4. Run Both Servers
```bash
bash run.sh
```

Or separately:
```bash
# Terminal 1
source venv/bin/activate && python manage.py runserver

# Terminal 2
cd frontend && npm start
```

---

## Project Structure
```
secure-commerce/
├── backend/          # Django settings, urls, wsgi
├── users/            # Custom user model, auth endpoints
├── products/         # Product & category management
├── cart/             # Shopping cart
├── orders/           # Order management & checkout
├── payments/         # Mock payment gateway
├── facial_auth/      # Face enrollment & verification
├── trust_management/ # Trusted devices, security events
├── frontend/
│   └── src/
│       ├── pages/    # All React pages
│       ├── components/ # Reusable components
│       ├── services/ # Axios API service
│       └── contexts/ # Auth & Cart contexts
├── .env              # Environment variables
├── requirements.txt
└── run.sh
```

---

## Key Features
| Feature | Implementation |
|---|---|
| Face Enrollment | Webcam → OpenCV → face_recognition embeddings → Fernet encrypted |
| Face Verification at Checkout | Required step before order placement |
| JWT Auth | Access (30min) + Refresh (7 days) tokens with rotation |
| Trusted Devices | Device tracking with risk scoring |
| Security Events Log | All auth events logged with IP and risk score |
| Mock Payment Gateway | Simulated checkout flow (replaceable with Stripe/Flutterwave) |
| Trust Badges | Visual HTTPS, Face Auth, Payment security indicators |
| Privacy Policy | GDPR-aligned data policy page |

---

## API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| POST | /api/users/register/ | Register |
| POST | /api/users/login/ | Login (JWT) |
| GET | /api/products/ | List products |
| GET/POST | /api/cart/ | View/add to cart |
| POST | /api/orders/checkout/ | Place order (requires face_verified=true) |
| POST | /api/facial-auth/enroll/ | Enroll face |
| POST | /api/facial-auth/verify/ | Verify face |
| GET | /api/trust/events/ | Security events |
| GET | /api/trust/indicators/ | Trust badge data |

---

## Security Controls
- **SQL Injection**: Django ORM (parameterized queries)
- **XSS**: React DOM escaping + DOMPurify
- **CSRF**: Django CSRF middleware + `CSRF_COOKIE_SECURE`
- **Password Hashing**: Django PBKDF2 (default)
- **Encryption**: Fernet (AES-128) for face embeddings
- **Rate Limiting**: DRF throttling (20 req/min anon, 100/min user)
- **Session Security**: JWT rotation + auto-expiry
# E--commerce-Application
# E--commerce-Application
