from flask import Blueprint, request, session, redirect, url_for, jsonify
from main.models import Admin, Teacher
from main.utils import is_admin, login_required, util_db_add, check_password_hash, generate_password_hash
from main.logger import event_logger, error_logger

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form.get('email','').strip().lower()
    password = request.form.get('password','')
    role = request.form.get('role','').strip().lower()

    if not email or not password:
        return redirect(url_for('index.login'))

    if role == 'admin':
        admin = Admin.query.filter_by(email=email, is_active=True).first()
        if admin and check_password_hash(admin.password, password):
            session['user'] = {
                'user_id': admin.id,
                'name': admin.name,
                'email': admin.email,
                'level': admin.level,
                'role': 'admin'
            }

            # Redirect based on admin.level
            if admin.level == 1:
                return redirect(url_for('admin.dashboard'))
            elif admin.level == 2:
                return redirect(url_for('sales.dashboard'))
            else:
                # fallback to general admin dashboard
                return redirect(url_for('admin.dashboard'))

        return redirect(url_for('index.login'))

    elif role == 'teacher':
        teacher = Teacher.query.filter_by(email=email, is_active=True).first()
        if teacher and check_password_hash(teacher.password, password):
            session['user'] = {
                'user_id': teacher.id,
                'name': teacher.name,
                'email': teacher.email,
                'role': 'teacher'
            }
            return redirect(url_for('teacher.dashboard'))
        return redirect(url_for('index.login'))

    else:
        # Unknown role → force to login page again
        return redirect(url_for('index.login'))


@auth_bp.route('/create_account', methods=['POST'])
@is_admin(1)
@login_required
def create_account():
    data = request.get_json()
    if not data:
        return jsonify({'success': True, 'error': 'No data provided'}), 400
    
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role','').strip().lower()

    if not all([name, email, password, role]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    if role == 'admin':
        if Admin.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400

        hashed_password = generate_password_hash(password)
        print(len(hashed_password))
        new_admin = Admin(
            name=name,
            email=email,
            password=hashed_password,
            level=2
        )
        result = util_db_add(new_admin)
        if not result.get('success'):
            return jsonify({'success': False, 'error': 'User creation error'}), 500
        return jsonify({'success': True, 'message': 'User created successfully', 'data': new_admin.to_dict()}), 200

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index.index'))

@auth_bp.route('/register_admin', methods=['POST'])
def register_admin():
    """
    Public endpoint to register a brand‐new Admin using JSON → { name, email, password, role }.
    (No @login_required, no @is_admin decorator.)

    Expected JSON payload:
      {
        "name": "Alice Admin",
        "email": "alice@example.com",
        "password": "supersafepw",
        "role": "admin"
      }
    Returns JSON { success: True/False, message: "...", data: { … } }.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON body provided'}), 400

    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', '').strip().lower()

    # Basic validation (exactly mimicking create_account’s checks)
    if not all([name, email, password, role]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    if role != 'admin':
        return jsonify({'success': False, 'error': 'Role must be "admin"'}), 400

    # Check for duplicate‐email
    if Admin.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'Email already exists'}), 400

    # Hash the password, set level=2 (exactly like create_account did)
    hashed_password = generate_password_hash(password)
    new_admin = Admin(
        name=name,
        email=email,
        password=hashed_password,
        level=2
    )

    result = util_db_add(new_admin)
    if not result.get('success'):
        # util_db_add returns something like {'success': False, 'error': '…'}
        return jsonify({'success': False, 'error': 'Database error while creating admin'}), 500

    # If successful, return the new_admin.to_dict() so client can inspect id/name/email.
    return jsonify({
        'success': True,
        'message': 'Admin user created successfully',
        'data': new_admin.to_dict()
    }), 200