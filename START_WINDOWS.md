# SIH26001 Landslide — Windows Complete Start Guide

## A. Backend setup

```cmd
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE\backend
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `backend\.env` with this for local testing:

```env
DATABASE_URL=postgresql://postgres:1234@localhost:5432/landslide_db
AUTH_SECRET=change-this-to-a-long-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
DEV_EMAIL_MODE=true
```

SMTP fields can be added later. Do not use `DEV_EMAIL_MODE=true` in production.

## B. Initialize/check DB

```cmd
python scripts\init_db.py
python scripts\check_setup.py
```

From the project root, seed demo monitoring points:

```cmd
cd ..
python database\seed_demo_data.py
```

## C. Start backend

```cmd
cd backend
venv\Scripts\activate
uvicorn main:app --reload
```

Test `http://127.0.0.1:8000/api/health` and expect `status=healthy`, `database=connected`.

## D. Start frontend (second terminal)

```cmd
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE\frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev build does not install the service worker.

## E. User registration

1. Open **New User**.
2. Enter a name, phone, a 12-digit test Aadhaar value, and email.
3. Click **Send Verification Code**.
4. With `DEV_EMAIL_MODE=true`, the demo OTP is shown on the page.
5. Enter the OTP and click **Verify & Continue**.
6. Dashboard opens after `/api/auth/me` succeeds.

Check pgAdmin:

```sql
SELECT id, name, email, phone, email_verified, created_at FROM app_users ORDER BY id DESC;
SELECT id, user_id, purpose, expires_at, used, created_at FROM email_otps ORDER BY id DESC LIMIT 10;
```

## F. Admin login

Use the exact `ADMIN_USERNAME` / `ADMIN_PASSWORD` values from `backend\.env`.

## G. First run after replacing an older ZIP

Chrome DevTools → Application → Service Workers → **Unregister** the old `ner-landslide-v1` worker. Then Application → Storage → **Clear site data** once. Close/reopen the tab. This is needed only for the old installed worker; new Vite development sessions are service-worker-free.

## H. Production

Set secure `AUTH_SECRET`, admin credentials and SMTP variables in Vercel. Set `DEV_EMAIL_MODE=false`. Never commit `.env`.
