from flask import Blueprint, request, session, render_template, redirect, url_for, jsonify
from main.models import Timetable, Teacher, Admin, Attendance
from main.utils import util_db_add, util_db_update, util_db_delete, generate_password_hash, login_required, is_admin

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@is_admin(2)
def dashboard():
    return redirect(url_for('admin.create_teacher'))
@admin_bp.route('/create/sales', methods=['GET', 'POST'])
@login_required
@is_admin(2)
def create_sales():
    if request.method == "GET":
        admins = Admin.query.filter_by(level=2)
        return render_template('create_sales_admin.html', admins=admins)

    # Else post request to create sales 
    data = request.get_json()
    if not data:
        return jsonify({'success': True, 'error': 'No data provided'}), 400
    
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role','').strip().lower()

    if not all([name, email, password, role]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    if role != 'admin':
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    if Admin.query.filter_by(email=email).first():
        return jsonify({'success' : False, 'error': 'Email already exists'}), 400

    hashed_password = generate_password_hash(password)
    new_admin = Admin(
        name=name,
        email=email,
        password=hashed_password,
    )
    result = util_db_add(new_admin)
    if not result.get('success'):
        return jsonify({'success': False, 'error': 'User creation error'}), 500
    admin = new_admin.to_dict()
    return jsonify({'success': True, 'message': 'User created successfully', 'data': admin}), 200

@admin_bp.route('/modify/sales', methods=['PUT', 'DELETE'])
@login_required
@is_admin(1)
def modify_sales():
    """
    PUT  → update admin's name/email/password
    DELETE → deactivate (or hard-delete) a admin
    """
    admin_id = request.json.get('id')
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({'success': False, 'error': 'Sales not found'}), 404

    if request.method == 'DELETE':
        admin.is_active = False
        result = util_db_update()
        if not result.get('success'): 
            return jsonify({'success': False, 'error': 'Failed to deactivate account'}), 500
        return jsonify({'success': True, 'message': 'Sales Account deactivated'}), 200

    # Otherwise, it's a PUT
    data = request.get_json()
    name = data.get('name','').strip()
    email = data.get('email','').strip().lower()
    password = data.get('password')  # optional; only if they want to update password
    is_active = data.get('is_active',None)

    if name:
        admin.name = name
    if email:
        # check duplicate:
        existing = Admin.query.filter(Admin.email == email, Admin.id != admin_id).first()
        if existing:
            return jsonify({'success': False, 'error': 'Email already in use'}), 400
        admin.email = email
    if is_active is not None:
        print(admin.is_active)
        admin.is_active = is_active

    if password:
        admin.password = generate_password_hash(password)

    result = util_db_update()
    if not result.get("success"):
        return jsonify({ 'success': False, 'error': 'Admin Updation Failed' }), 500

    data = admin.to_dict()

    return jsonify({ 'success': True, 'message': 'Admin updated', 'admin': data}), 200


@admin_bp.route('/create/teacher', methods=['GET','POST'])
@login_required
@is_admin(1)
def create_teacher():
    if request.method == "GET":
        teachers = Teacher.query.all()
        return render_template('admin_dashboard.html', teachers=teachers)

    data = request.get_json()
    name = data.get('name','').strip()
    email = data.get('email','').strip().lower()
    password = data.get('password','')
    address = data.get('address','').strip().lower()
    role = data.get('role','').strip().lower()
    mobile = data.get('mobile','').strip().lower()
    pan_number = data.get('pan_number','').strip().upper()
    pay_per_lecture_raw = data.get('pay_per_lecture')
    bankInfo = data.get('paymentDetails',{})

    if not name or not email or not password or not role or not address or not mobile or not pan_number or pay_per_lecture is not None:
        return jsonify({'success': False, 'error': 'All fields (including name, email, password, role, address, mobile, pan_number, pay_per_lecture) are required'}), 400

    try:
        pay_per_lecture = float(pay_per_lecture_raw)
        if pay_per_lecture < 0:
            return jsonify({'success': False, 'error': 'pay_per_lecture cannot be negative'}), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'pay_per_lecture must be a number'}), 400

    try:
        int(mobile)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Mobile must be a number'}), 400

    if bankInfo != {}:
        if bankInfo.get('ifscCode') is not None and len(bankInfo.get('ifscCode')) != 11:
            return jsonify({'success': False, 'error': 'IFSC must be of 11 characters'}), 400
        if bankInfo.get('AccountNumber') is not None and len(bankInfo.get('AccountNumber')) > 18:
            return jsonify({'success': False, 'error': 'Invalid Account Number'}), 400
        if bankInfo.get('AccountNumber') is not None:
            try:
                int(bankInfo.get('AccountNumber'))
            except (TypeError, ValueError):
                return jsonify({'success': False, 'error': 'Account Number must be a number'}), 400     

    if len(pan_number) > 10:
        return jsonify({'success': False, 'error': 'PAN Card Number Length Must be 10 Digits'}), 400

    # Check for duplicate Teacher email
    if Teacher.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'Email already exists'}), 400

    hashed_pw = generate_password_hash(password)
    new_teacher = Teacher(
        name=name,
        email=email,
        password=hashed_pw,
        address=address,
        role=role,
        mobile=mobile,
        pan_number=pan_number,
        pay_per_lecture=pay_per_lecture,
        bank_info=bankInfo
    )
    result = util_db_add(new_teacher)
    if not result.get('success'):
        return jsonify({ 'success': False, 'error': 'Teacher Creation Failed'}), 500
    
    teacher = new_teacher.to_dict()
    return jsonify({ 'success': True, 'message': 'Teacher created successfully', 'teacher': teacher }), 200

# ── Edit a Teacher (PUT / DELETE) ─────────────────────────────────────────────────
@admin_bp.route('/modify/teacher', methods=['PUT', 'DELETE'])
@login_required
@is_admin(1)
def modify_teacher():
    """
    PUT  → update teacher's name/email/password
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

    # Otherwise, it's a PUT
    data = request.get_json()
    name = data.get('name','').strip()
    email = data.get('email','').strip().lower()
    password = data.get('password')  # optional; only if they want to update password
    address = data.get('address','').strip().lower()
    role = data.get('role','').strip().lower()
    mobile = data.get('mobile','').strip().lower()
    pan_number = data.get('pan_number','').strip().upper()
    pay_raw = data.get('pay_per_lecture')  # ← new
    is_active = data.get('is_active',None)
    bankInfo = data.get('paymentDetails',{})

    if name:
        teacher.name = name
    if email:
        existing = Teacher.query.filter(Teacher.email == email, Teacher.id != teacher_id).first()
        if existing:
            return jsonify({'success': False, 'error': 'Email already in use'}), 400
        teacher.email = email
    if password:
        teacher.password = generate_password_hash(password)
    if address:
        teacher.address=address
    if role:
        teacher.role = role
    if mobile:
        try:
            int(mobile)
            teacher.mobile = mobile
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Mobile must be a number'}), 400
    if pan_number:
        if len(pan_number) > 10:
            return jsonify({'success': False, 'error': 'PAN Card Number Length Must be 10 Digits'}), 400
        teacher.pan_number = pan_number
        
    if pay_raw is not None:
        try:
            pay_val = float(pay_raw)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'pay_per_lecture must be a number'}), 400
        if pay_val < 0:
            return jsonify({'success': False, 'error': 'pay_per_lecture cannot be negative'}), 400
        teacher.pay_per_lecture = pay_val

    if is_active is not None:
        teacher.is_active = is_active

    if bankInfo:
        if bankInfo != {}:
            if bankInfo.get('ifscCode') is not None and len(bankInfo.get('ifscCode')) != 11:
                return jsonify({'success': False, 'error': 'IFSC must be of 11 characters'}), 400
            if bankInfo.get('AccountNumber') is not None and len(bankInfo.get('AccountNumber')) > 18:
                return jsonify({'success': False, 'error': 'Invalid Account Number'}), 400
            if bankInfo.get('AccountNumber') is not None:
                try:
                    int(bankInfo.get('AccountNumber'))
                except (TypeError, ValueError):
                    return jsonify({'success': False, 'error': 'Account Number must be a number'}), 400     
            teacher.bank_info = bankInfo

    result = util_db_update()
    if not result.get("success"):
        return jsonify({ 'success': False, 'error': 'Teacher Updation Failed' }), 500

    data = teacher.to_dict()

    return jsonify({ 'success': True, 'message': 'Teacher updated', 'teacher': data}), 200

@admin_bp.route('/timetables')
@login_required
@is_admin(1)
def timetables():
    entries = Timetable.query.order_by(Timetable.day_of_week, Timetable.start_time).all()
    teachers = Teacher.query.filter_by(is_active=True).all()
    return render_template('timetable.html', entries=entries, teachers=teachers)

@admin_bp.route('/timetable/create', methods=['POST'])
@login_required
@is_admin(1)
def create_timetable():
    data = request.get_json()
    try:
        subject = data['subject'].strip()
        teacher_id = int(data['teacher_id'])
        day_of_week = int(data['day_of_week'])
        start_time = data['start_time']
        grade = data['grade'].strip()
    except (KeyError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid input data'}), 400

    # Validate day_of_week (0-6)
    if not 0 <= day_of_week <= 6:
        return jsonify({'success': False, 'error': 'Invalid day of week'}), 400

    new_entry = Timetable(
        subject=subject,
        teacher_id=teacher_id,
        day_of_week=day_of_week,
        start_time=start_time,
        grade=grade
    )
    result = util_db_add(new_entry)
    if not result.get('success'):
        return jsonify({'success': False, 'error': 'Creation failed'}), 500
        
    return jsonify({ 'success': True, 'data': new_entry.to_dict()}), 200

@admin_bp.route('/timetable/modify', methods=['PUT', 'DELETE'])
@login_required
@is_admin(1)
def modify_entry():
    data = request.get_json()
    entry = Timetable.query.get(data.get('id'))
    if not entry:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    if request.method == 'DELETE':
        # Check if there are any attendance records
        if Attendance.query.filter_by(timetable_id=entry.id).first():
            return jsonify({'success': False, 'error': 'Cannot delete timetable with attendance records'}), 400
        result = util_db_delete(entry)
        if not result.get('success'):
            return jsonify({'success': False, 'error': 'Deletion failed'}), 500
        return jsonify({'success': True}), 200

    # PUT → update
    try:
        entry.subject = data['subject'].strip()
        entry.teacher_id = int(data['teacher_id'])
        entry.day_of_week = int(data['day_of_week'])
        entry.start_time = data['start_time']
        entry.grade = data['grade'].strip()
    except (KeyError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid data'}), 400

    # Validate day_of_week (0-6)
    if not 0 <= entry.day_of_week <= 6:
        return jsonify({'success': False, 'error': 'Invalid day of week'}), 400

    result = util_db_update()
    if not result.get('success'):
        return jsonify({'success': False, 'error': 'Update failed'}), 500
    return jsonify({'success': True, 'entry': entry.to_dict()}), 200