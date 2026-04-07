# EduGrant (Carmona CAYDO Scholarship Assistance)

Local development setup for the EduGrant web system (Django + HTML/CSS).

## Prerequisites
- Python 3.13+

## Run locally
Open this folder in VS Code/Cursor: `edugrant/`

Then in a terminal:

```bash
cd backend

# If your venv isn't created yet:
python3 -m venv ../.venv

# Install dependencies
../.venv/bin/python -m pip install -r ../requirements.txt

# Create local env file (first time only)
cp .env.example .env

# Run migrations
../.venv/bin/python manage.py migrate

# Create an admin account
../.venv/bin/python manage.py createsuperuser

# Start server
../.venv/bin/python manage.py runserver
```

Now open:
- Home page: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

