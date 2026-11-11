# Local Talena demo environment

This setup creates a disposable SQLite database with a working customer login,
a demo company, project, team and three synthetic candidates with completed
assessment results. It does not connect to PostgreSQL/Azure, contact Sova, or
send email.

## Windows PowerShell

From the repository root, activate the project's virtual environment if it is
not already active, then run:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings_local"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_local_demo
.\.venv\Scripts\python.exe manage.py runserver
```

On the first run, the command prompts for a password for
`demo@talena.local`. Use that username and password to sign in to the local
Talena app. Rerunning the command refreshes the same synthetic candidates and
does not reset the login password.

The local database is `db.local.sqlite3`, which is ignored by Git. The selected
settings are held in the current PowerShell window; set
`DJANGO_SETTINGS_MODULE` again in a new window.

## Demo content

The command reuses `seed_team_report_demo` to create three fictional candidates
with different personality, motivation, ability and team-style results. It can
be rerun safely. Generated records are marked as synthetic demo data and use
`example.invalid` email addresses.

The command refuses to run unless the selected settings use local SQLite,
`DEBUG=True`, and a local/development/test environment.
