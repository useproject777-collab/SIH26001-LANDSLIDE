# SIH26001 Landslide — Windows Verification Checklist

## 1. Backend health

With the backend running:

```text
http://127.0.0.1:8000/api/health
```

Expected:

```json
{"status":"healthy","database":"connected"}
```

## 2. Check auth tables and location count

From `backend` with the venv active:

```cmd
python scripts\check_setup.py
```

The output should show `app_users table: app_users`, `email_otps table: email_otps`, and a non-zero location count after seeding.

## 3. Test registration without the frontend

This isolates the backend/database/auth flow. In a second CMD window:

```cmd
curl.exe -X POST "http://127.0.0.1:8000/api/auth/register" -F "name=Test User" -F "email=test-user@example.com" -F "phone=9876543210" -F "aadhaar=123456789012"
```

With `DEV_EMAIL_MODE=true`, the response contains a six-digit `dev_code`.

## 4. Verify the OTP

Replace `123456` with the actual `dev_code`:

```cmd
curl.exe -X POST "http://127.0.0.1:8000/api/auth/verify-email" -F "email=test-user@example.com" -F "otp=123456"
```

The response should contain `token`, `role=user`, `user_id` and `email`.

## 5. Check the database in pgAdmin

```sql
SELECT id, name, email, phone, email_verified, created_at
FROM app_users
ORDER BY id DESC;

SELECT id, user_id, purpose, expires_at, used, created_at
FROM email_otps
ORDER BY id DESC
LIMIT 10;
```

After successful verification, the user row should have `email_verified = true`, and the OTP row should have `used = true`.

## 6. Test authenticated live risk

Copy the token returned from registration verification and use:

```cmd
curl.exe -H "Authorization: Bearer YOUR_TOKEN" "http://127.0.0.1:8000/api/live-risk/1"
```

Without the token, `/api/live-risk/1` correctly returns `401 Login required`.

## 7. Frontend

```cmd
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE\frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Expected first screen: **New User / User Login / Admin**. The dashboard must not render before authentication.

## 8. Old service worker

When replacing an older ZIP for the first time, Chrome DevTools → Application → Service Workers → **Unregister** the old `ner-landslide-v1` worker, then Application → Storage → **Clear site data** once. New Vite development runs do not install a service worker.
