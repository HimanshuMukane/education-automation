from flask import Blueprint, request, session, redirect, url_for, jsonify
from main.models import Admin, Teacher
from main.utils import is_admin, login_required, util_db_add, check_password_hash, generate_password_hash
from main.logger import event_logger, error_logger

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    role = request.form.get('role','').strip().lower()
    if not email or not password:
        event_logger.warning(f"error because of these fields with value{email=} {password=}")
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
            event_logger.info(f"Admin logged in successful")
            return redirect(url_for('index.index'))
        event_logger.warning(f"login error for admin")
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
            event_logger.info(f"teacher logged in successful")
            return redirect(url_for('index.index'))
        event_logger.warning(f"login error for teacher")
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