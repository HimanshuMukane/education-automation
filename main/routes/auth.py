from flask import Blueprint, request, session, redirect, url_for, flash, jsonify
from main.models import Admin, Teacher, Sales
from main.utils import check_password_hash, generate_password_hash
from main.extensions import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        role = data.get('role', '').lower()

        if not all([email, password, role]):
            return jsonify({'success': False, 'error': 'Email, password and role are required'}), 400

        # Validate role
        if role not in ['admin', 'teacher', 'sales']:
            return jsonify({'success': False, 'error': 'Invalid role selected'}), 400

        # Check user based on role
        user = None
        if role == 'admin':
            user = Admin.query.filter_by(email=email).first()
        elif role == 'teacher':
            user = Teacher.query.filter_by(email=email).first()
        elif role == 'sales':
            user = Sales.query.filter_by(email=email).first()

        if not user:
            return jsonify({'success': False, 'error': 'Invalid email or role'}), 401

        if not user.is_active:
            return jsonify({'success': False, 'error': 'Account is inactive. Please contact administrator.'}), 401

        if not check_password_hash(user.password, password):
            return jsonify({'success': False, 'error': 'Invalid password'}), 401

        # Create session data based on role
        session_data = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': role
        }

        # Add role-specific data
        if role == 'admin':
            session_data.update({
                'is_admin': True
            })
        elif role == 'teacher':
            session_data.update({
                'pay_per_lecture': user.pay_per_lecture
            })
        elif role == 'sales':
            session_data.update({
                'commission_rate': user.commission_rate
            })

        session['user'] = session_data
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'redirect': url_for(f'{role}.dashboard')
        }), 200

    except Exception as e:
        # Log the error here if you have a logging system
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }), 500

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index.login'))

@auth_bp.route('/register_admin', methods=['POST'])
def register_admin():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        required_fields = ['name', 'email', 'password']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Validate email format
        email = data['email'].strip().lower()
        if not '@' in email or not '.' in email:
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400

        # Check if email already exists
        if Admin.query.filter_by(email=email).first():
            return jsonify({'success': False, 'error': 'Email already registered'}), 400

        # Validate password strength
        password = data['password']
        if len(password) < 8:
            return jsonify({'success': False, 'error': 'Password must be at least 8 characters long'}), 400

        # Create new admin
        admin = Admin(
            name=data['name'].strip(),
            email=email,
            password=generate_password_hash(password),
            is_active=True
        )

        db.session.add(admin)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Admin account created successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }), 500