# EvacLocate

A Django application for evacuation-location management and a disaster-response dashboard.

## Features

- Account registration, login, and logout
- Separate user registration/login and staff administrator login
- Add, view, edit, and delete evacuation locations
- Each account can only see and manage its own locations
- Response dashboard with incident, deployment, personnel, and rescue metrics
- Separate community dashboard for regular users with personal report tracking, public alerts, shelters, and supplies
- Barangay conditions, incident alerts, team messages, and reminders
- Staff-only dashboard operations and profile editing
- Staff-only user management; users can browse evacuation centers and supplies
- Staff-managed evacuation center CRUD with coordinates, list map, and individual center maps
- Users can submit and manage their own flood reports and rescue requests; staff can review all reports and update response status
- SQLite database and Django admin

Each evacuation center stores a name, address, optional description, capacity, status, and optional map coordinates. Staff manage centers from the Evacuation Centers page using add, edit, detail, and delete screens. Center coordinates must be entered as latitude and longitude together; pins appear on the map only when coordinates are set. Map tiles require an internet connection.
The dashboard data is entered and maintained by staff in Django admin. The page checks for updates every 30 seconds; it does not subscribe to earthquake or flood agency feeds. To display map pins, a staff admin must set latitude and longitude for barangays. The map uses OpenStreetMap tiles via Leaflet, so map tiles require an internet connection.

The initial migration adds San Isidro, San Basillo, Dila-Dila, San Agustin, San Jose, San Juan, Santa Monica, San Matias, and Becuran. Admins can add or rename barangays and update their rescue counts and condition from `/admin/`.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

If the virtual environment is already created, activate it before running Django commands. Alternatively, use the venv interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open http://127.0.0.1:8000/ to create a regular user account or sign in. The separate administrator sign-in is at `/accounts/admin-login/`; administrator registration is at `/accounts/admin-register/`. Public registration always creates a regular account. To enable administrator self-registration, a trusted operator generates a one-time invitation code from the project command line. The code expires after 24 hours by default, is stored hashed in the database, and can only be used once. Admin registrants receive staff access but not superuser privileges. Create the first superuser with `python manage.py createsuperuser`; only a superuser can grant superuser access or register administrators from User Management. The dashboard and sidebar pages are available to signed-in users. Staff admins can manage accounts, centers, supplies, incidents, reports, deployments, barangay conditions and rescue counts, messages, reminders, and map coordinates from the app pages and `/admin/`. Regular users can browse centers and supply inventory and can submit, edit, or delete their own flood reports and rescue requests. They cannot view other users' submitted reports or update report response status.

Generate a one-time administrator invitation in PowerShell:

```powershell
.\.venv\Scripts\python.exe manage.py create_admin_invite
```

Copy the printed code and give it only to the intended administrator; they can then register at `/accounts/admin-register/`. The code is shown only once. To set a different expiry, for example 2 hours, use `.\.venv\Scripts\python.exe manage.py create_admin_invite --expires-hours 2`.

Flood and rescue reports in this starter app are operational records, not an emergency dispatch service. For urgent situations, users should also contact local emergency services directly.

For deployment, set `DJANGO_SECRET_KEY` to a private, randomly generated key, set `DJANGO_DEBUG=false`, and set `DJANGO_ALLOWED_HOSTS` to the allowed hostnames. The default settings are for local development only.
