# SIH26001 - Vercel + Neon Deployment Guide

This project is designed so the React frontend and FastAPI API can be served from the same Vercel domain. The frontend uses relative `/api/...` requests in production, while local development uses `http://127.0.0.1:8000`.

## 1. Neon database

Use the existing Neon project/database if you already created one. Copy the **pooled PostgreSQL connection string** from Neon and keep it private.

The value should look similar to:

```text
postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

Do not commit this value to GitHub.

## 2. Initialize Neon schema from Windows

Open Command Prompt in the project root:

```cmd
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE
cd backend
copy .env.example .env
notepad .env
```

Set:

```env
DATABASE_URL=YOUR_NEON_POOLED_CONNECTION_STRING
AUTH_SECRET=PASTE_A_LONG_RANDOM_SECRET_HERE
ADMIN_USERNAME=admin
ADMIN_PASSWORD=CREATE_A_STRONG_ADMIN_PASSWORD
DEV_EMAIL_MODE=true
```

For the first local test, `DEV_EMAIL_MODE=true` is intentionally supported. It returns the OTP in the API response so registration can be tested without SMTP. Never use this mode on the public production deployment.

Then:

```cmd
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE\backend
venv\Scripts\activate
python scripts\init_db.py
python scripts\check_setup.py
```

Expected setup check includes:

```text
DATABASE_URL: OK
AUTH_SECRET: OK
ADMIN_USERNAME: OK
ADMIN_PASSWORD: OK
app_users table: app_users
email_otps table: email_otps
```

## 3. Seed NER monitoring points into Neon

From the project root, with the same backend environment active:

```cmd
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE
python database\seed_demo_data.py
```

The seed locations are prototype/demo monitoring points. They are not official government sensor stations.

## 4. Local backend test

```cmd
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE\backend
venv\Scripts\activate
uvicorn main:app --reload
```

Check:

```text
http://127.0.0.1:8000/api/health
```

It should return a healthy database response.

## 5. Local frontend test

Open a second Command Prompt:

```cmd
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE\frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The first page is now the website landing page. Click:

- **Login to Monitoring** -> User Login
- **Create User Account** -> New User registration
- **Admin Login** -> Admin login

The development Vite HMR WebSocket has been disabled in this package to avoid the `WebSocket handshake 400` problem. Use normal browser refresh (`Ctrl+R`) after editing files.

## 6. Test a new user locally

1. Click **Create User Account**.
2. Enter name, phone, 12-digit Aadhaar and email.
3. Click **Send Verification Code**.
4. With `DEV_EMAIL_MODE=true`, the page displays the demo OTP.
5. Enter that OTP.
6. The server verifies the OTP and returns a bearer token.
7. The user dashboard opens.
8. The user record is stored in `app_users`; the OTP is stored hashed in `email_otps` and marked used after verification.

To verify in PostgreSQL:

```sql
SELECT id, name, email, phone, email_verified, created_at
FROM app_users
ORDER BY id DESC;

SELECT id, user_id, purpose, used, expires_at, created_at
FROM email_otps
ORDER BY id DESC;
```

## 7. Vercel production environment variables

In Vercel:

**Project -> Settings -> Environment Variables -> Production**

Add these server-side variables:

```text
DATABASE_URL
AUTH_SECRET
ADMIN_USERNAME
ADMIN_PASSWORD
DEV_EMAIL_MODE
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_FROM
```

Recommended production values:

```env
DATABASE_URL=YOUR_NEON_POOLED_CONNECTION_STRING
AUTH_SECRET=NEW_LONG_RANDOM_PRODUCTION_SECRET
ADMIN_USERNAME=your-admin-name
ADMIN_PASSWORD=your-strong-admin-password
DEV_EMAIL_MODE=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-gmail@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=your-gmail@gmail.com
```

If using Gmail SMTP, use a Google **App Password**, not your normal Gmail password.

Do not put `DATABASE_URL`, `AUTH_SECRET`, `ADMIN_PASSWORD` or `SMTP_PASSWORD` in frontend variables such as `VITE_*`. Vite frontend variables are exposed to the browser.

After changing Vercel environment variables, trigger a new deployment.

## 8. Vercel deployment

If the GitHub repository is already connected to Vercel:

```cmd
git add .
git commit -m "add landing page and fix auth flow"
git push origin main
```

Vercel will create a new deployment from the `main` branch.

If using the Vercel CLI instead:

```cmd
npm install -g vercel
vercel login
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE
vercel link
vercel deploy --prod
```

## 9. Production verification order

After deployment, test in this order:

1. `/api/health` -> database connected.
2. `/` -> landing page appears.
3. Click **New User** -> registration page appears.
4. Register a new email -> real SMTP OTP should arrive.
5. Verify OTP -> user dashboard opens.
6. Search a city -> location results appear.
7. Use map click -> coordinate risk appears.
8. Use **My Location** -> browser location permission appears.
9. Submit a citizen report -> it is saved for the logged-in user.
10. Logout -> landing page appears.
11. Admin Login -> private admin console appears.
12. Admin can review citizen reports and uploaded media.

## 10. Important production rules

- `DEV_EMAIL_MODE=false` in production.
- Use a strong random `AUTH_SECRET`.
- Use a strong admin password.
- Never commit `.env`.
- Keep Neon connection strings private.
- The Aadhaar field is only stored as a one-way application hash in this prototype. This is **not** UIDAI authentication/e-KYC.
- Demo slope/monitoring-point values are marked as demo data and require replacement/validation for real operational use.
- Risk thresholds are prototype thresholds and are not a validated disaster-management decision rule.
