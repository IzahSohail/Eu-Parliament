# European Parliament Voting Analysis

## Overview

This Django web application analyzes and visualizes voting patterns of Members of the European Parliament (MEPs) during the 10th parliamentary term (2024–2029).

It collects voting records, MEP information, and political group affiliations, helping users explore how their representatives have voted over time.

## Purpose

Imagine you are a European citizen curious about your elected representatives.  
With this application, you can:

- Explore how your MEPs voted.
- See shifts in political group affiliations over time.
- Understand how political groups align on various issues.
- Make better-informed decisions for future elections.

## Features

- **Voting Behavior Analysis**: See how each MEP voted on different proposals.
- **Committee & Rapporteur Tracking**: Understand the legislative role of each MEP.
- **Political Group Shifts**: Track MEPs switching political groups.
- **Dynamic Database**: Easily refresh with new data using Django commands.
- **Simple UI**: Browse and filter votes easily.

## Technology Stack

- **Backend**: Django (Python)
- **Database**: PostgreSQL
- **Frontend**: Django templates (HTML, CSS)

## Example Screenshots

_(Optional: You can add screenshots later if needed)_

## Installation and Setup

### 1. Clone the Repository

If you received a `.zip` file, extract it. Otherwise:

```bash
git clone https://github.com/your-repo/eu-parliament-votes
cd eu-parliament-votes
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
CREATE DATABASE eu_parliament_db;
```

### 5. Configure Database Settings

Open `eu_parliament/settings.py`.  
Update the `DATABASES` section:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'eu_parliament_db',       # Your database name
        'USER': 'your_postgres_username',  # Your PostgreSQL username
        'PASSWORD': 'your_postgres_password',  # Your PostgreSQL password
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Save the file.

### 6. Apply Django Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Import Data into Database

If you received `.csv` files:

```sql
COPY core_voteinfo(vote_id, code, interinstitutional_file_no, label, date, caller, rapporteur, committee_responsible)
FROM '/path/to/vote_info_ep10.csv'
DELIMITER ','
CSV HEADER;
```

```sql
COPY core_votemapping(vote_id, mep_id, vote_type)
FROM '/path/to/vote_mapping_ep10.csv'
DELIMITER ','
CSV HEADER;
```

```sql
COPY core_membership(mep_id, start_date, end_date, group_id)
FROM '/path/to/current_memberships.csv'
DELIMITER ','
CSV HEADER;
```

Adjust the file paths according to your local machine.

### 8. Run the Development Server

```bash
python manage.py runserver
```

Visit [http://localhost:8000](http://localhost:8000) to access the application.

## Useful Django Management Commands

- Fetch updated MEP membership data:

```bash
python manage.py fetch-mep-membership-data
```

- Import votes from XML:

```bash
python manage.py import-vote-data
```

- Export current MEP memberships:

```bash
python manage.py export-current-memberships
```

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
