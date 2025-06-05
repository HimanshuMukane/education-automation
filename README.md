# Flask Project Setup Guide
---

## 🔧 Setup Instructions

### 1. Prerequisites

Make sure you have the following installed:

- **Python** ≥ 3.10  
- **Node.js** ≥ 18.x (for SCSS)
- **Sass (Dart Sass)** compiler installed globally:

```bash
npm install -g sass
````

---

### 2. Setting Up Virtual Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# For Windows:
venv\Scripts\activate

# For macOS/Linux:
source venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🧰 Using `utils.py` and Logging

* Utility functions like:

  * `util_set_params(...)`
  * `util_normalize_string(...)`
  * `util_upload_image(...)`
  * `util_db_add(...)`, `util_db_update(...)`, `util_db_delete(...)`

* All actions and errors are automatically logged via:

  * `event_logger` → for normal operation events
  * `error_logger` → for exceptions and failures

**Logger setup** should be present in `main/logger.py`. Make sure it's imported as:

```python
from main.logger import event_logger, error_logger
```

---

## 🔁 SCSS Compilation (Auto-Compile to CSS)

You can write your styles in `main/static/scss/`. To compile:

```bash
sass --watch main/static/scss:main/static/css --style compressed --source-map
```

This will:

* Watch your SCSS files live
* Compile to minified CSS
* Generate source maps for debugging

---

## 🗃️ Database Migration with Flask-Migrate

### 🔰 First Time Setup

```bash
# 1. Initialize migration folder (only once)
flask db init

# 2. Define your SQLAlchemy models

# 3. Generate migration files
flask db migrate -m "initial migration"

# 4. Apply migration to database
flask db upgrade
```

---

### 👨‍💻 Developer Workflow (After Model Changes)

```bash
# 1. Make changes to SQLAlchemy models

# 2. Generate new migration
flask db migrate -m "describe changes"

# 3. Apply changes to DB
flask db upgrade
```

---

### 🔁 After Pulling Changes from Git

If someone else updated the models and added migrations:

```bash
# Just apply the migration
flask db upgrade
```

---

## ✅ Summary of Required Tools

| Tool        | Purpose                | Install Command                               |
| ----------- | ---------------------- | --------------------------------------------- |
| Python      | Backend runtime        | [Download](https://www.python.org/downloads/) |
| Node.js     | SCSS compiler runtime  | [Download](https://nodejs.org/)               |
| Sass (Dart) | Compile SCSS to CSS    | `npm install -g sass`                         |
| pip         | Install Python modules | Comes with Python                             |
| venv        | Virtual environment    | Comes with Python                             |
| Flask CLI   | Run Flask + migrations | Comes via `requirements.txt`                  |

---

## 🏁 Run Your App

```bash
flask run
```

Or, if you have a app file like `app.py`:

```bash
python app.py
```

---

Happy building! 🚀