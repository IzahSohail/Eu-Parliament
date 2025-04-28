# European Parliament Voting Analysis

## Overview

This Django web application analyzes and visualizes voting patterns of Members of the European Parliament (MEPs) for all parliamentary terms.

It collects voting records, MEP information, and political group affiliations, helping users explore how their representatives have voted over time.

## Technology Stack

- **Backend**: Django (Python)
- **Database**: PostgreSQL
- **Frontend**: Django templates (HTML, CSS)

## Installation and Setup

### 1. Clone the Repository

If you received a `.zip` file, extract it. Otherwise:

```bash
git clone https://github.com/IzahSohail/Eu-Parliament.git
cd Eu-Parliament
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

If no `requirements.txt` is provided, install manually:

```bash
pip install django psycopg2-binary requests beautifulsoup4 lxml
```

### 4. Set Up PostgreSQL Database

- Open **pgAdmin** or terminal.
- Create a new PostgreSQL database:

```sql
CREATE DATABASE my_database;
```

### 5. Configure Database Settings

In order for Django to connect to your PostgreSQL database, you need to update the database settings.

### Step 1: Open the Settings File

Navigate to the following file inside your project:

Open `django_project/settings.py`.  

Find the section that looks like this:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Step 3: Fill In Your Database Information
Replace the empty fields with your local PostgreSQL information:

NAME: The name of your database (e.g., my_database).

USER: Your PostgreSQL username (e.g., postgres).

PASSWORD: Your PostgreSQL password.

HOST: Keep as localhost.

PORT: Keep as 5432 (unless you use a different port).

Save the file.

### 6. Apply Django Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

Visit [http://localhost:8000](http://localhost:8000) to access the application.

## Troubleshooting

- Database connection errors: Double-check your `settings.py`.
- Missing dependencies: Run:

```bash
pip install -r requirements.txt
```

- Django migration issues: Run:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Credits

Developed for academic and research purposes.
