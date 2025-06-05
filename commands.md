python -m venv env
or
virtualenv env

-------------------------------------------------------------------------

.\env\Scripts\activate

-------------------------------------------------------------------------

npm install -g sass

-------------------------------------------------------------------------

python -m pip install -r requirements.txt
or
pip install -r requirements.txt

-------------------------------------------------------------------------

python -m pip freeze > requirements.txt
or 
pip freeze > requirements.txt

-------------------------------------------------------------------------

sass --watch main/static/scss:main/static/css --style compressed --source-map

-------------------------------------------------------------------------

### First Time Setup

# 1. Initialize migration folder (only once)
flask db init

# 2. Define your SQLAlchemy models
# 3. Generate migration files
flask db migrate -m "initial migration"

# 4. Apply migration to database
flask db upgrade

-------------------------------------------------------------------------

### Developer Workflow (After Model Changes)

# 1. Make changes to SQLAlchemy models

# 2. Generate new migration
flask db migrate -m "describe changes"

# 3. Apply changes to DB
flask db upgrade

-------------------------------------------------------------------------

### After Pulling Changes from Git

If someone else updated the models and added migrations:

# Just apply the migration
flask db upgrade

-------------------------------------------------------------------------
### If you are using Windows and encounter issues with the above commands:

# Open PowerShell as Administrator
Set-ExecutionPolicy RemoteSigned -Scope LocalMachine

