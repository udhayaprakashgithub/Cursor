# Django Scheduler + Cron Runner

This project is a full Django implementation of the scheduler interface.

## Features
- Upload a `main.py` script.
- Choose a virtual environment folder path.
- Run script once, at interval minutes, or with cron expression.
- Run immediately, enable/disable, and delete tasks.
- Store latest output and execution time.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Cron formats
Use `cron_expression` in standard crontab format:
`minute hour day_of_month month day_of_week`
Example: `*/15 * * * *`
