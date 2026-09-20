# Fixes in this version

1. Added a proper public landing/index page before authentication.
2. Added clear User Login, New User and Admin Login entry points.
3. Added Back to website navigation from the authentication screen.
4. Fixed Admin Console logout button so it no longer references the Dashboard-only `t` variable.
5. Removed the public-dashboard attempt to GET admin-only citizen reports after submitting a report.
6. User OTP verification now reloads `/api/auth/me` before opening the dashboard.
7. Added auth-expired event handling so a 401 clears the stale token and returns the user to login.
8. Disabled Vite HMR WebSocket in this package to remove the localhost WebSocket handshake 400 error seen in the reported setup. Normal `Ctrl+R` refresh remains available.
9. Fixed `backend/scripts/check_setup.py` syntax so the setup checker can be compiled/run.
10. Added `DEPLOY_VERCEL_NEON.md` with the complete Neon + Vercel production setup sequence.
11. Added an updated Windows quick-start flow.
12. Python source and backend scripts were syntax-checked with `py_compile`.

## Important

The browser console errors `401 Login required` and `403 Admin access required` are expected when protected endpoints are called without the correct authenticated role. The updated UI no longer calls the admin-only citizen-report list from the normal user dashboard.
