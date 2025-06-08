from flask import Blueprint, request, session, render_template, redirect, url_for, jsonify
from main.models import Timetable, Teacher, Admin
from main.utils import util_db_add, util_db_update, util_db_delete, generate_password_hash, login_required, is_admin

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@is_admin(2)
def dashboard():
    teachers = Teacher.query.all()
    return render_template('admin_dashboard.html', teachers=teachers)

@admin_bp.route('/create/sales')
@login_required
@is_admin(2)
def create_sales():
    admins = Admin.query.filter_by(level=2)
    return render_template('create_sales_admin.html', admins=admins)


@admin_bp.route('/create-teacher', methods=['POST'])
@login_required
@is_admin(1)
def create_teacher():
    data = request.get_json()
    name = data.get('name','').strip()
    email = data.get('email','').strip().lower()
    password = data.get('password','')
    pay_per_lecture_raw = data.get('pay_per_lecture')
    bankInfo = data.get('paymentDetails',{})
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
        bank_info=bankInfo
    )
    result = util_db_add(new_teacher)
    if not result.get('success'):
        return jsonify({
            'success': False,
            'error': 'Teacher Creation Failed',
        }), 500
    return jsonify({
        'success': True,
        'message': 'Teacher created successfully',
        'teacher': {
            'id': new_teacher.id,
            'name': new_teacher.name,
            'email': new_teacher.email,
            'is_active': 'Active' if new_teacher.is_active else 'Inactive',
            'pay_per_lecture': float(new_teacher.pay_per_lecture),
            "bank_info":new_teacher.bank_info
        }
    }), 200

# ── Edit a Teacher (PUT / DELETE) ─────────────────────────────────────────────────
@admin_bp.route('/modify-teacher', methods=['PUT', 'DELETE'])
@login_required
@is_admin(1)
def modify_teacher():
    """
    PUT  → update teacher’s name/email/password
    DELETE → deactivate (or hard-delete) a teacher
    """
    teacher_id = request.json.get('id')
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({'success': False, 'error': 'Teacher not found'}), 404

    if request.method == 'DELETE':
        teacher.is_active = False
        result = util_db_update()
        if not result.get('success'): 
            return jsonify({'success': False, 'error': 'Failed to deactivate account'}), 500
        return jsonify({'success': True, 'message': 'Teacher deactivated'}), 200

    # Otherwise, it’s a PUT
    data = request.get_json()
    name = data.get('name','').strip()
    email = data.get('email','').strip().lower()
    password = data.get('password')  # optional; only if they want to update password
    pay_raw = data.get('pay_per_lecture')  # ← new
    bankInfo = data.get('paymentDetails',{})
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
    
    if bankInfo:
        teacher.bank_info = bankInfo

    result = util_db_update()
    if not result.get("success"):
        return jsonify({
            'success': False,
            'error': 'Teacher Updation Failed',
        }), 500
    return jsonify({
        'success': True,
        'message': 'Teacher updated',
        'teacher': {
            'id': teacher.id,
            'name': teacher.name,
            'email': teacher.email,
            'pay_per_lecture': teacher.pay_per_lecture,
            'is_active': 'Active' if teacher.is_active else 'Inactive',
            'bank_info': teacher.bank_info
        }
    }), 200

@admin_bp.route('/timetables')
@login_required
@is_admin(1)
def timetables():
    entries = Timetable.query.all()
    teachers = Teacher.query.filter_by(is_active=True).all()
    return render_template('timetable.html', entries=entries, teachers=teachers)

@admin_bp.route('/timetable/create', methods=['POST'])
@login_required
@is_admin(1)
def create_timetable():
    data = request.get_json()
    try:
        date = data['date']
        grade = data['grade'].strip()
        subject = data['subject'].strip()
        start_time = data['start_time']
        end_time = data['end_time']
        teacher_id = int(data['teacher_id'])
    except (KeyError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid input data'}), 400

    new_entry = Timetable(
        date=date,
        grade=grade,
        subject=subject,
        start_time=start_time,
        end_time=end_time,
        teacher_id=teacher_id
    )
    result = util_db_add(new_entry)
    if not result.get('success'):
        return jsonify({'success': False, 'error': 'Creation failed'}), 500
    resp = new_entry.to_dict()
    return jsonify({
        'success': True,
        'data': resp
    }), 200

@admin_bp.route('/timetable/modify', methods=['PUT', 'DELETE'])
@login_required
@is_admin(1)
def modify_entry():
    data = request.get_json()
    entry = Timetable.query.get(data.get('id'))
    if not entry:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    if request.method == 'DELETE':
        # Soft delete flag
        result = util_db_delete(entry)
        if not result.get('success'):
            return jsonify({'success': False, 'error': 'Deletion failed'}), 500
        return jsonify({'success': True}), 200

    # PUT → update
    try:
        entry.date = data['date']
        entry.grade = data['grade'].strip()
        entry.subject = data['subject'].strip()
        entry.start_time = data['start_time']
        entry.end_time = data['end_time']
        entry.teacher_id = int(data['teacher_id'])
    except (KeyError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid data'}), 400
    result = util_db_update()
    if not result.get('success'):
        return jsonify({'success': False, 'error': 'Update failed'}), 500
    resp = {}
    return jsonify({'success': True, 'entry': resp}), 200