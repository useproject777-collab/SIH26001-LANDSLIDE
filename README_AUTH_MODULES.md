# SIH26001 Authentication, Privacy, Admin & Language Modules

## User access
- New user registration: name, phone, email, Aadhaar (12 digits).
- Email OTP verification proves control of the email address.
- User login uses email OTP.
- Aadhaar is never stored in plaintext; only a one-way hash is stored.
- The prototype performs only a 12-digit format check. It does **not** perform official UIDAI authentication/e-KYC. Official Aadhaar authentication requires an authorised AUA/Sub-AUA integration and UIDAI infrastructure.

## Admin access
- Separate Admin tab on the login page.
- Credentials come from `ADMIN_USERNAME` and `ADMIN_PASSWORD` in backend environment variables.
- Citizen photos/videos/documents are not shown on the public dashboard.
- Admin Console lists reports and provides authenticated media links.

## Email warning
- High/Critical risk for a logged-in user can trigger one email warning per risk level per 30 minutes.
- Configure Gmail SMTP with a free Gmail account and an App Password. Google requires 2-Step Verification for App Passwords.
- Required variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`.
- Local demo can use `DEV_EMAIL_MODE=true`, which returns the OTP in the API response; never enable this in production.

## Location
- Browser GPS/network geolocation: **Use My Location**.
- Manual latitude/longitude input.
- City/place search through Open-Meteo geocoding.
- Map click selects a coordinate and calculates live weather + terrain/slope risk.

## Languages
The UI selector includes English, Tamil, Hindi, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, Odia, Assamese and Urdu. These are bundled static UI translations, so no translation API cost is required.

## Free-cost design
The prototype uses React/Vite, FastAPI, PostgreSQL/PostGIS, Leaflet/OpenStreetMap, Open-Meteo, scikit-learn and static translations. Open-Meteo's free API is intended for non-commercial use and has documented rate limits; attribution is required.

## Important data note
The application is an SIH prototype. Risk thresholds and demo terrain/sensor values must not be presented as scientifically validated operational warnings. Official deployment would require validated datasets, government/authorised feeds, security review, privacy controls, and operational agreements.
