# ── main/admin.py ───────────────────────────────────────────────────────────────
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
from main.models import Teacher
from main.extensions import db
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
def dashboard():
    user = session.get('user')
    if not user or user.get('role') != 'admin' or user.get('level') != 1:
        return redirect(url_for('index.index'))
    teachers = Teacher.query.order_by(Teacher.id.desc()).all()
    return render_template('admin_dashboard.html', teachers=teachers)

@admin_bp.route('/teacher/create', methods=['POST'])
def create_teacher():
    """
    Expect JSON body with:
      {
        "name": "Full Name",
        "email": "teacher@example.com",
        "password": "somepassword",
        "pay_per_lecture": 250.00
      }
    """
    user = session.get('user')
    if not user or user.get('role') != 'admin' or user.get('level') != 1:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    pay_per_lecture_raw = data.get('pay_per_lecture')

    # Basic validation
    if not name or not email or not password or pay_per_lecture_raw is None:
        return jsonify({'success': False, 'error': 'All fields (including pay_per_lecture) are required'}), 400

    # Convert pay_per_lecture to float
    try:
        pay_per_lecture = float(pay_per_lecture_raw)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'pay_per_lecture must be a number'}), 400

    if pay_per_lecture < 0:
        return jsonify({'success': False, 'error': 'pay_per_lecture cannot be negative'}), 400

    # Check for duplicate Teacher email
    if Teacher.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'Email already exists'}), 400

    hashed_pw = generate_password_hash(password)
    new_teacher = Teacher(
        name=name,
        email=email,
        password=hashed_pw,
        pay_per_lecture=pay_per_lecture,
        is_active=True
    )
    db.session.add(new_teacher)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Teacher created successfully',
        'teacher': {
            'id': new_teacher.id,
            'name': new_teacher.name,
            'email': new_teacher.email,
            'pay_per_lecture': float(new_teacher.pay_per_lecture)
        }
    }), 200

# ── Edit a Teacher (PUT / DELETE) ─────────────────────────────────────────────────
@admin_bp.route('/teacher/<int:teacher_id>', methods=['PUT', 'DELETE'])
def modify_teacher(teacher_id):
    """
    PUT  → update teacher’s name/email/password
    DELETE → deactivate (or hard‐delete) a teacher
    """
    user = session.get('user')
    if not user or user.get('role') != 'admin' or user.get('level') != 1:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    teacher = Teacher.query.get_or_404(teacher_id)

    if request.method == 'DELETE':
        # Option A: Soft-delete (mark inactive)
        teacher.is_active = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'Teacher deactivated'}), 200

    # Otherwise, it’s a PUT
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')  # optional; only if they want to update password
    pay_raw = data.get('pay_per_lecture')  # ← new

    if name:
        teacher.name = name
    if email:
        # check duplicate:
        existing = Teacher.query.filter(Teacher.email == email, Teacher.id != teacher_id).first()
        if existing:
            return jsonify({'success': False, 'error': 'Email already in use'}), 400
        teacher.email = email
    if pay_raw is not None:
        try:
            pay_val = float(pay_raw)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'pay_per_lecture must be a number'}), 400
        if pay_val < 0:
            return jsonify({'success': False, 'error': 'pay_per_lecture cannot be negative'}), 400
        teacher.pay_per_lecture = pay_val

    if password:
        teacher.password = generate_password_hash(password)


    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Teacher updated',
        'teacher': {
            'id': teacher.id,
            'name': teacher.name,
            'email': teacher.email
        }
    }), 200
