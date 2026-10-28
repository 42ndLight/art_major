# ArtMajor — Artist Business Workspace

A Django-based platform for independent artists and creative studios to manage customers, projects, invoices, and payments.

---

## Tech Stack

| Layer    | Technology                                   |
| -------- | -------------------------------------------- |
| Backend  | Django 4.2+                                  |
| Database | PostgreSQL                                   |
| Frontend | HTMX, Alpine.js, Tailwind CSS (CDN), daisyUI |
| Auth     | Email-based custom `User` model (UUID PK)    |
| Static   | WhiteNoise                                   |
| Tests    | pytest-django                                |

---

## Local Setup

### 1. Clone the repository

```bash
git clone <repo-url> art_major
cd art_major
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `dj-database-url` is also required for reading `DATABASE_URL`. Add it if not already listed:
>
> ```bash
> pip install dj-database-url
> ```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your local values:

```ini
SECRET_KEY=your-locally-generated-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://artuser:artpass@localhost:5432/artmajor
```

Generate a secret key quickly:

```bash
python -c "from django.utils.crypto import get_random_string; print(get_random_string(50))"
```

### 5. Create the PostgreSQL database

```bash
psql -U postgres
```

```sql
CREATE USER artuser WITH PASSWORD 'artpass';
CREATE DATABASE artmajor OWNER artuser;
GRANT ALL PRIVILEGES ON DATABASE artmajor TO artuser;
\q
```

### 6. Run migrations

```bash
python manage.py migrate
```

### 7. (Optional) Create a superuser for the admin panel

```bash
python manage.py createsuperuser
```

### 8. Start the development server

```bash
python manage.py runserver
```

The app will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 9. Create your first artist account

Navigate to [http://127.0.0.1:8000/accounts/signup/](http://127.0.0.1:8000/accounts/signup/) and register.

After signing in you'll land on the dashboard at `/dashboard/`.

---

## Running Tests

```bash
pytest
```

Or using the Makefile:

```bash
make test
```

Tests use `pytest-django` and read settings from `artmajor.settings.local` (configured in `pytest.ini`).

> Tests require a running PostgreSQL instance matching your `.env` `DATABASE_URL`.

---

## Makefile Commands

| Command               | Description                           |
| --------------------- | ------------------------------------- |
| `make install`        | Install Python dependencies           |
| `make migrate`        | Run `python manage.py migrate`        |
| `make makemigrations` | Run `python manage.py makemigrations` |
| `make run`            | Start the development server          |
| `make test`           | Run the test suite with pytest        |
| `make lint`           | Run `python manage.py check`          |

---

## URL Map

| URL                  | View                      | Auth required |
| -------------------- | ------------------------- | ------------- |
| `/`                  | Redirect to `/dashboard/` | —             |
| `/dashboard/`        | DashboardView             | ✅            |
| `/accounts/signup/`  | SignUpView                | ❌            |
| `/accounts/login/`   | LoginView                 | ❌            |
| `/accounts/logout/`  | LogoutView (POST)         | ✅            |
| `/settings/profile/` | ProfileView               | ✅            |
| `/health/`           | HealthView                | ❌            |
| `/admin/`            | Django admin              | Staff only    |

---

## Project Structure

```
art_major/
├── artmajor/           # Django project package
│   ├── settings/
│   │   ├── base.py     # Shared settings
│   │   └── local.py    # Dev-only settings (reads .env)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/           # Custom user, artist profile, auth
├── core/               # Dashboard, health check
├── templates/          # Global base.html + partials
├── static/             # Static assets (Stage 2+)
├── tests/              # Test suite
├── manage.py
├── requirements.txt
├── pytest.ini
├── Makefile
└── .env.example
```

---

## Stage Roadmap

| Stage | Scope | Status |
|---|---|---|
| **1** | Scaffold, auth, dashboard, tests | ✅ Current |
| 2 | Customers & Projects | 🔜 |
| 3 | Invoices & Payments | 🔜 |
| 4 | Africa's Talking SMS commands and notifications | In progress |
| 5 | Reporting & analytics | 🔜 |

## Africa's Talking SMS (feature-AT)

Configure `AFRICASTALKING_API_KEY`, `AFRICASTALKING_USERNAME`, and `AFRICASTALKING_ENVIRONMENT` (`sandbox` by default). Set a long random `AFRICASTALKING_INBOUND_WEBHOOK_TOKEN`, then configure the AT inbound SMS callback to:

```text
https://<your-host>/webhooks/africastalking/inbound/<AFRICASTALKING_INBOUND_WEBHOOK_TOKEN>/
```

Artists add their phone number in Settings → Profile and request a verification code. Only a verified artist number can issue commands. Supported messages:

```text
CUSTOMER|Jane Doe|+254712345678
INVOICE|Jane Doe|5000|KES|Logo design
```

Invoices are created as drafts for review. The app records inbound provider IDs for idempotency, stores only a digest of SMS text, and replies to the artist. Test with Africa's Talking sandbox credentials and destinations before production. Verify the callback fields and delivery behavior against the configured AT account before live use.
