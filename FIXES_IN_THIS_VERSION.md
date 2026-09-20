# What was fixed in this version

## Authentication
- The app now renders `New User / User Login / Admin` before any protected dashboard request.
- User registration stores the user in `app_users`, creates an OTP in `email_otps`, and returns a demo OTP when `DEV_EMAIL_MODE=true`.
- Email verification marks `email_verified=true` and returns a signed bearer token.
- Login OTP has the same working demo-OTP path.
- `/api/auth/me` returns the actual user record for verified users.
- Expired/invalid user tokens are cleared by the frontend.

## Browser cache / Vite development
- The service worker is no longer registered during Vite development.
- The frontend removes an old `ner-landslide-*` service worker/cache when it detects one.
- Production service worker cache is versioned to `v2` and navigation uses network-first behavior.
- Vite HMR is configured explicitly for `localhost:5173`.

## Dashboard/API
- Frontend API base can be configured with `VITE_API_BASE`; local development still defaults to `http://127.0.0.1:8000`.
- Citizen report submission no longer performs an admin-only GET after a successful user POST. This previously made a successful submission look like a 403 failure.
- Admin page no longer references an undefined translation variable.
- Authenticated dashboard bootstrap is explicit.

## Database setup
- Added `backend/scripts/init_db.py`.
- Added `backend/scripts/check_setup.py`.
- Updated the Windows guide and testing checklist with exact commands and SQL checks.

## Important prototype limits
- Aadhaar is stored only as a one-way hash and this project does not perform official UIDAI authentication/e-KYC.
- Risk thresholds are prototype rules and need validation against representative historical data before operational deployment.
- Seeded monitoring points are demo/prototype points, not claims of official government sensor stations.
