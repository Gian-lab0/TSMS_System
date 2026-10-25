# Teacher Schedule Management System (TSMS)

Flask + SQLite web application. This updated version adds admin controls, schedule approval, SHS-specific choices, multi-day entry, teacher period details, leave requests, and responsive layouts.

## Features
- Admin dashboard: approve/reject teacher-submitted schedules, edit/delete schedule entries, review timetable, reset registered account passwords, review the latest 200 login attempts, and approve/decline sick leave or wellness break requests.
- Teacher schedule submissions stay pending until approved; approved schedules appear in the timetable and teacher assigned-period list.
- Multi-select Monday–Friday to add the same class period on several days. Conflicts are skipped for each conflicting day.
- Clicking the assigned-period count opens the teacher's approved sections, days, times, and subjects.
- Senior High School has Acads / Tech-Pro programs, the requested sections, and SHS-specific teacher and subject choices.
- Mobile-responsive layout for phones and desktop browsers.

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run `python -m venv .venv` then activate it.
4. Run `pip install -r requirements.txt`.
5. Set a long random `TSMS_SECRET_KEY` environment variable before deployment.
6. Run `python app.py`.
7. Open `http://127.0.0.1:5000`.

The first account in a new database becomes admin. For an existing database, the first existing account is promoted to admin if there is no admin yet. For production, explicitly set `ADMIN_EMAIL` to the intended admin email before starting the app. Admin account assignment should be reviewed before sharing the system.

## Publish a link usable on other devices
The project is now configured for a WSGI host using the included `Procfile`. To make a public link, deploy this folder to a Python web host such as Render:
- Create a new web service from a private Git repository containing this folder.
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Set `TSMS_SECRET_KEY` to a strong random secret and `ADMIN_EMAIL` to the administrator's registered email.
- Configure persistent disk/storage for `teacher_schedule_management.db`; otherwise SQLite data may be lost when the host restarts or redeploys.
- After deployment, use the host's HTTPS URL on phones and other computers.

A public URL cannot be created from the source code alone; deployment and hosting account setup are required. Do not use the development server for production.

## Important production notes
- This prototype uses SQLite, so configure persistent storage or migrate to managed PostgreSQL for a multi-user production deployment.
- Passwords are hashed. Password reset is admin-only in the dashboard; the existing self-service reset page is retained for local demo compatibility and should be replaced with email verification before public production.
- Login logs contain account emails and timestamps; restrict access to admins and follow your school's privacy policy.
- For public deployment, add CSRF protection, HTTPS-only secure session cookies, database backups, and a tested account recovery process before handling real school data.
- The app's default secret is for local development only; always set `TSMS_SECRET_KEY` in deployment.


## Timetable draft and final approval workflow

- Teachers select weekdays using checkbox controls and save schedule entries as drafts.
- The timetable status icon opens the saved timetable even when the section is incomplete.
- Admins review and edit entries from Admin Dashboard. They approve the whole section timetable only when it is complete.
- Any new entry, deletion, or edit marks that section as incomplete again.
- The timetable page offers the official print button only after section-level approval.
- Login and home interfaces use a green/yellow theme.
