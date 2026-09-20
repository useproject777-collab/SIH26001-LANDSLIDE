# Windows Quick Start - SIH26001

## Backend

```cmd
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE\backend
venv\Scripts\activate
copy .env.example .env
notepad .env
python scripts\init_db.py
python scripts\check_setup.py
uvicorn main:app --reload
```

## Frontend (new terminal)

```cmd
cd C:\Users\sasin\Downloads\SIH26001-LANDSLIDE\frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Website flow

1. Landing page opens first.
2. **Login to Monitoring** -> User Login.
3. **Create User Account** -> New User + email OTP verification.
4. **Admin Login** -> private Admin Console.
5. After logout, the landing page appears again.

## Local OTP testing

For local testing only, use:

```env
DEV_EMAIL_MODE=true
```

The API returns a demo OTP so you can complete registration without an email provider.

## Production

Use `DEV_EMAIL_MODE=false` and configure SMTP. See `DEPLOY_VERCEL_NEON.md`.
