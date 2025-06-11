from flask import Blueprint, request, session, render_template, redirect, url_for, jsonify
from main.models import Timetable, Teacher, Admin, Attendance, StudentInvoice, Sales
from main.utils import util_db_add, util_db_update, util_db_delete, generate_password_hash, login_required
from main.extensions import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect(url_for('index.login'))
    return render_template('admin_dashboard.html')

@admin_bp.route('/create/sales', methods=['GET', 'POST'])
@login_required
def create_sales():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect(url_for('index.login'))
        
    if request.method == "GET":
        # Get all sales accounts
        sales_accounts = Sales.query.filter_by(is_active=True).all()
        return render_template('create_sales_admin.html', sales_accounts=sales_accounts)

    # Else post request to create sales 
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    mobile = data.get('mobile', '').strip()
    address = data.get('address', '').strip()
    pan_number = data.get('pan_number', '').strip()
    bank_info = data.get('bank_info', {})
    commission_rate = data.get('commission_rate', 10.0)

    if not all([name, email, password, mobile, address, pan_number]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    if Sales.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'Email already exists'}), 400

    hashed_password = generate_password_hash(password)
    new_sales = Sales(
        name=name,
        email=email,
        password=hashed_password,
        mobile=mobile,
        address=address,
        pan_number=pan_number,
        bank_info=bank_info,
        commission_rate=commission_rate
    )
    result = util_db_add(new_sales)
    if not result.get('success'):
        return jsonify({'success': False, 'error': 'User creation error'}), 500
    sales = new_sales.to_dict()
    return jsonify({'success': True, 'message': 'Sales account created successfully', 'data': sales}), 200

@admin_bp.route('/modify/sales', methods=['PUT', 'DELETE'])
@login_required
def modify_sales():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect(url_for('index.login'))
        
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
def create_teacher():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect(url_for('index.login'))
        
    if request.method == "GET":
        teachers = Teacher.query.all()
        return render_template('create_teacher_admin.html', teachers=teachers)

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

    if not name or not email or not password or not role or not address or not mobile or not pan_number:
        return jsonify({'success': False, 'error': 'All fields (including name, email, password, role, address, mobile, pan_number) are required'}), 400

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

    if any(value for value in bankInfo.values()):
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

@admin_bp.route('/modify/teacher', methods=['PUT', 'DELETE'])
@login_required
def modify_teacher():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect(url_for('index.login'))
        
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
        if len(pan_number) != 10:
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
        if any(value for value in bankInfo.values()):
            if bankInfo.get('ifscCode') != '' and len(bankInfo.get('ifscCode')) != 11:
                return jsonify({'success': False, 'error': 'IFSC must be of 11 characters'}), 400
            if bankInfo.get('AccountNumber') != '' and len(bankInfo.get('AccountNumber')) > 18:
                return jsonify({'success': False, 'error': 'Invalid Account Number'}), 400
            if bankInfo.get('AccountNumber') != '':
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
def timetables():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect(url_for('index.login'))
        
    entries = Timetable.query.order_by(Timetable.day_of_week, Timetable.start_time).all()
    teachers = Teacher.query.filter_by(is_active=True).all()
    return render_template('timetable.html', entries=entries, teachers=teachers)

@admin_bp.route('/timetable/create', methods=['POST'])
@login_required
def create_timetable():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect(url_for('index.login'))
        
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
def modify_entry():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect(url_for('index.login'))
        
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

@admin_bp.route('/teacher-analytics')
@login_required
def teacher_analytics():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect(url_for('index.login'))
        
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_, or_
    
    # Get all active teachers
    teachers = Teacher.query.filter_by(is_active=True).all()
    analytics = []
    
    # Get selected month and year from query params
    selected_month = request.args.get('month', datetime.now().month)
    selected_year = request.args.get('year', datetime.now().year)
    
    for teacher in teachers:
        # Get all attendance records for this teacher
        attendance_records = Attendance.query.join(Timetable).filter(
            or_(
                Timetable.teacher_id == teacher.id,
                Attendance.proxy_id == teacher.id
            ),
            db.extract('month', Attendance.date) == int(selected_month),
            db.extract('year', Attendance.date) == int(selected_year)
        ).all()
        
        # Calculate metrics
        total_classes = len(attendance_records)
        proxy_classes = sum(1 for record in attendance_records if record.is_proxy and record.proxy_id == teacher.id)
        regular_classes = sum(1 for record in attendance_records if not record.is_proxy and record.timetable.teacher_id == teacher.id)
        absent_classes = sum(1 for record in attendance_records 
            if record.timetable.teacher_id == teacher.id 
            and record.is_proxy 
            and record.proxy_id != teacher.id
        )
        
        # Get monthly earnings
        monthly_earnings = sum(
            teacher.pay_per_lecture 
            for record in attendance_records 
            if record.is_present and (
                (record.is_proxy and record.proxy_id == teacher.id) or
                (not record.is_proxy and record.timetable.teacher_id == teacher.id)
            )
        )
        
        # Get subject distribution
        subject_distribution = {}
        for record in attendance_records:
            if record.is_present and (
                (record.is_proxy and record.proxy_id == teacher.id) or
                (not record.is_proxy and record.timetable.teacher_id == teacher.id)
            ):
                subject = record.timetable.subject
                subject_distribution[subject] = subject_distribution.get(subject, 0) + 1
        
        # Get grade distribution
        grade_distribution = {}
        for record in attendance_records:
            if record.is_present and (
                (record.is_proxy and record.proxy_id == teacher.id) or
                (not record.is_proxy and record.timetable.teacher_id == teacher.id)
            ):
                grade = record.timetable.grade
                grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
        
        # Get day-wise distribution
        day_distribution = {i: 0 for i in range(7)}
        for record in attendance_records:
            if record.is_present and (
                (record.is_proxy and record.proxy_id == teacher.id) or
                (not record.is_proxy and record.timetable.teacher_id == teacher.id)
            ):
                day = record.timetable.day_of_week
                day_distribution[day] += 1
        
        # Calculate attendance consistency
        total_scheduled = len(attendance_records)
        total_present = sum(1 for record in attendance_records 
            if record.is_present and (
                (record.is_proxy and record.proxy_id == teacher.id) or
                (not record.is_proxy and record.timetable.teacher_id == teacher.id)
            )
        )
        attendance_rate = (total_present / total_scheduled * 100) if total_scheduled > 0 else 0
        
        # Compile analytics for this teacher
        teacher_analytics = {
            'id': teacher.id,
            'name': teacher.name,
            'email': teacher.email,
            'total_classes': total_classes,
            'proxy_classes': proxy_classes,
            'regular_classes': regular_classes,
            'absent_classes': absent_classes,
            'monthly_earnings': monthly_earnings,
            'attendance_rate': round(attendance_rate, 2),
            'subject_distribution': subject_distribution,
            'grade_distribution': grade_distribution,
            'day_distribution': day_distribution,
            'pay_per_lecture': teacher.pay_per_lecture
        }
        
        analytics.append(teacher_analytics)
    
    # Generate months and years for dropdown
    current_year = datetime.now().year
    years = list(range(current_year - 1, current_year + 1))
    months = [
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ]
    
    return render_template('teacher_analytics.html', 
                         analytics=analytics,
                         months=months,
                         years=years,
                         selected_month=selected_month,
                         selected_year=selected_year)

@admin_bp.route('/sales-analytics')
@login_required
def sales_analytics():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return redirect(url_for('index.login'))
        
    from datetime import datetime
    from sqlalchemy import func, and_, or_
    
    # Get all active sales admins (level 2)
    sales_admins = Admin.query.filter_by(is_active=True).all()
    analytics = []
    
    # Get selected month and year from query params
    selected_month = request.args.get('month', datetime.now().month)
    selected_year = request.args.get('year', datetime.now().year)
    
    for admin in sales_admins:
        # Get all student invoices created by this sales admin
        invoices = StudentInvoice.query.filter(
            StudentInvoice.created_by == admin.name,
            db.extract('month', StudentInvoice.date) == int(selected_month),
            db.extract('year', StudentInvoice.date) == int(selected_year)
        ).all()
        
        # Calculate metrics
        total_amount = sum(invoice.fees_paid for invoice in invoices)
        commission = total_amount * 0.10  # 10% commission
        
        # Get student details for each invoice
        student_details = []
        for invoice in invoices:
            student = invoice.student
            student_details.append({
                'name': f"{student.fname} {student.lname}",
                'date': invoice.date,
                'amount': invoice.fees_paid
            })
        
        # Compile analytics for this sales admin
        admin_analytics = {
            'id': admin.id,
            'name': admin.name,
            'email': admin.email,
            'total_amount': total_amount,
            'commission': commission,
            'student_details': student_details
        }
        
        analytics.append(admin_analytics)
    
    # Generate months and years for dropdown
    current_year = datetime.now().year
    years = list(range(current_year - 1, current_year + 1))
    months = [
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ]
    
    return render_template('sales_analytics.html', 
                         analytics=analytics,
                         months=months,
                         years=years,
                         selected_month=selected_month,
                         selected_year=selected_year)