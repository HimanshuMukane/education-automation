import uuid
from imghdr import what as whatImg

from re import sub as reg_sub
from os import makedirs as makeDirectory
from os.path import join as pathJoin

from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from main.extensions import db, bcrypt
from main.logger import event_logger, error_logger

from flask import request, session, redirect, url_for, jsonify
from .models import Admin
from functools import wraps
# ── main/utils.py ────────────────────────────────────────────────────────────────


def generate_password_hash(plain_password: str) -> str:
    """
    Generate a secure password hash using bcrypt.
    Args:
        plain_password (str): The plain text password to hash
    Returns:
        str: The hashed password as a utf-8 string
    """
    return bcrypt.generate_password_hash(plain_password).decode('utf-8')


def check_password_hash(stored_hash: str, candidate_password: str) -> bool:
    """
    Check if a candidate password matches the stored hash.
    Supports both bcrypt and Werkzeug hashes for backward compatibility.
    
    Args:
        stored_hash (str): The stored hash from the database
        candidate_password (str): The plain text password to check
    Returns:
        bool: True if the password matches, False otherwise
    """
    try:
        # Try bcrypt first
        return bcrypt.check_password_hash(stored_hash, candidate_password)
    except ValueError:
        # If bcrypt fails, try Werkzeug's check_password_hash
        from werkzeug.security import check_password_hash as werkzeug_check
        try:
            return werkzeug_check(stored_hash, candidate_password)
        except Exception:
            # If both methods fail, return False
            return False


def util_set_params(**kwargs) -> dict:
    """
    Creates and returns a dictionary from provided keyword arguments.

    Returns:
        dict: A dictionary containing all the keyword arguments.
    """
    event_logger.info(f"Set params called with keys: {list(kwargs.keys())}")
    return {key: value for key, value in kwargs.items()}


def util_normalize_string(string: str) -> dict | None:
    """
    Normalizes a string into multiple common naming conventions.

    Args:
        string (str): The input string to normalize.

    Returns:
        dict | None: A dictionary with normalized string formats, or None if input is empty.
    """
    if not string:
        event_logger.warning("util_normalize_string called with empty input")
        return None

    string = reg_sub(r'\s+', ' ', string.strip())
    unified = reg_sub(r'[-_]', ' ', string)

    words = unified.split()
    title = ' '.join(word.capitalize() for word in words)
    cleaned = '-'.join(word.lower() for word in words)
    snake = '_'.join(word.lower() for word in words)
    camel = words[0].lower() + ''.join(word.capitalize() for word in words[1:])
    pascal = ''.join(word.capitalize() for word in words)

    event_logger.info(f"Normalized string '{string}' to multiple cases")
    return {
        "original": string,
        "title": title,
        "cleaned": cleaned,
        "snake_case": snake,
        "camel_case": camel,
        "pascal_case": pascal
    }


def util_upload_image(image_file: FileStorage, filename: str, upload_folder: str, allowed_extensions: set[str] = None) -> dict:
    """
    Uploads an image to a specified folder after validating type and securing the filename.

    Args:
        image_file (FileStorage): The uploaded image file from the request.
        filename (str): Desired base filename (without extension).
        upload_folder (str): Directory to upload the image to.
        allowed_extensions (set[str], optional): Set of allowed file extensions.

    Returns:
        dict: Result status with success flag, message, and saved filename & path.
    """
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}

    def is_allowed(filename: str, stream) -> bool:
        ext = filename.rsplit('.', 1)[-1].lower()
        valid_ext = ext in allowed_extensions
        valid_mime = whatImg(stream) in allowed_extensions
        return valid_ext and valid_mime

    try:
        if not image_file or not image_file.filename:
            error_logger.error("No image file provided for upload")
            return {'success': False, 'error': 'No image file provided'}

        file_ext = image_file.filename.rsplit('.', 1)[-1].lower()
        safe_filename = secure_filename(filename.replace(" ", "-"))
        unique_suffix = uuid.uuid4().hex[:8]
        final_filename = f"{safe_filename}_{unique_suffix}.{file_ext}"
        filepath = pathJoin(upload_folder, final_filename)

        makeDirectory(upload_folder, exist_ok=True)

        event_logger.info(f"Uploading image: {final_filename} to {upload_folder}")

        image_file.seek(0)
        if not is_allowed(image_file.filename, image_file.stream):
            error_logger.error(f"Invalid image file type: {image_file.filename}")
            return {'success': False, 'error': 'Invalid image file type'}

        image_file.seek(0)
        image_file.save(filepath)

        event_logger.info(f"Image uploaded successfully: {final_filename}")
        return {
            'success': True,
            'message': 'Image uploaded successfully',
            'filename': final_filename,
            'filepath': filepath
        }

    except Exception as e:
        error_logger.error(f"Image upload failed: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def util_db_add(obj) -> dict:
    """
    Adds an object to the database and commits the session.

    Args:
        obj: SQLAlchemy model instance to be added.

    Returns:
        dict: Status message with success flag.
    """
    try:
        db.session.add(obj)
        db.session.commit()
        event_logger.info(f"Added to DB: {obj}")
        return {'success': True, 'message': 'Added successfully'}
    except Exception as e:
        error_logger.error(f"DB add failed: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def util_db_delete(obj) -> dict:
    """
    Deletes an object from the database and commits the session.

    Args:
        obj: SQLAlchemy model instance to be deleted.

    Returns:
        dict: Status message with success flag.
    """
    try:
        db.session.delete(obj)
        db.session.commit()
        event_logger.info(f"Deleted from DB: {obj}")
        return {'success': True, 'message': 'Deleted successfully'}
    except Exception as e:
        error_logger.error(f"DB delete failed: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def util_db_update() -> dict:
    """
    Commits any pending changes to the database session.

    Returns:
        dict: Status message with success flag.
    """
    try:
        db.session.commit()
        event_logger.info(f"Database session updated successfully")
        return {'success': True, 'message': 'Updated successfully'}
    except Exception as e:
        error_logger.error(f"DB update failed: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

# ──────────── Wrappers ────────────

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            event_logger.warning(f"User Key Not In Session")
            return jsonify({"success":False, "error": "login required for performing action"}), 403              
        return f(*args, **kwargs)
    return decorated_function

def is_admin(max_level=1):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get('user')
            role = user.get("role")
            level = user.get("level")
            admin_id = user.get("user_id")
            if not user or not role or role != 'admin' or not admin_id or not level or level < max_level:
                event_logger.warning(f"Unauthorized access attempt by user: {user.get('email', 'unknown') if user else 'unknown'}")
                return jsonify({"success":False, "error": "Access denied for non-admin access requests"}), 403
                
            admin = Admin.query.filter_by(id=admin_id, is_active=True).first()
            if not admin:
                event_logger.warning(f"Admin account not found for admin id {admin_id}")
                return jsonify({"success":False, "error": "Access denied for non-admin access requests"}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator