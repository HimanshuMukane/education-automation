import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from flask import Blueprint, request, session, current_app, render_template, redirect, url_for, flash, send_file
from sqlalchemy import or_

from werkzeug.utils import secure_filename

from main.extensions import db
from main.models import Timetable, Teacher, Attendance
from main.utils import login_required

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    return '.' in filename and ext in current_app.config.get('ALLOWED_EXTENSIONS', {'mp4','mov','avi','mkv'})

@teacher_bp.route('/mark-attendance', methods=['GET'])
@login_required
def mark_attendance():
    user = session.get('user')
    if not user or user.get('role') != 'teacher':
        return redirect(url_for('index.login'))

    today = datetime.now().date()
    teacher = Teacher.query.filter_by(email=user.get('email')).first()
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('index.login'))

    # Get dates for last 6 days
    dates = [(today - timedelta(days=i)) for i in range(6)]
    lectures = []
    
    for date in dates:
        day_of_week = date.weekday()
        templates = Timetable.query.filter_by(day_of_week=day_of_week).all()
        
        for template in templates:
            # Check if attendance record exists
            attendance = Attendance.query.filter_by(
                timetable_id=template.id,
                date=date
            ).first()
            
            # If no attendance record exists, create one
            if not attendance:
                attendance = Attendance(
                    timetable_id=template.id,
                    date=date
                )
                db.session.add(attendance)
                db.session.commit()
            
            # Only add to lectures list if not marked
            if not attendance.is_present:
                lectures.append({
                    'id': attendance.id,
                    'subject': template.subject,
                    'grade': template.grade,
                    'start_time': template.start_time,
                    'teacher_name': template.assigned_teacher.name,
                    'date': date,
                    'is_present': attendance.is_present,
                    'is_proxy': attendance.is_proxy,
                    'proxy_name': attendance.proxy_teacher.name if attendance.proxy_teacher else None
                })
    
    # Sort lectures by date and time
    lectures.sort(key=lambda x: (x['date'], x['start_time']))
    
    return render_template('mark_attendance.html', lectures=lectures)

@teacher_bp.route('/mark-attendance', methods=['POST'])
@login_required
def handle_attendance_upload():
    user = session.get('user')
    teacher = Teacher.query.filter_by(email=user.get('email')).first()
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('teacher.mark_attendance'))

    attendance_id = request.form.get('attendance_id')
    file = request.files.get('video')
    if not attendance_id or not file or not allowed_file(file.filename):
        flash('Invalid lecture selection or file type. Only videos allowed.', 'danger')
        return redirect(url_for('teacher.mark_attendance'))

    attendance = Attendance.query.get(attendance_id)
    if not attendance or attendance.is_present:
        flash('Lecture not found or already marked.', 'danger')
        return redirect(url_for('teacher.mark_attendance'))

    is_proxy = (attendance.timetable.teacher_id != teacher.id)
    attendance.is_present = True
    if is_proxy:
        attendance.is_proxy = True
        attendance.proxy_id = teacher.id

    base_name = f"{attendance.timetable.grade}_{attendance.timetable.subject}_{attendance.date.isoformat()}_{attendance.timetable.teacher_id}_{attendance.timetable.start_time.strftime('%H%M')}"
    prefix = 'proxy_' if is_proxy else ''
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], prefix + base_name)
    os.makedirs(upload_dir, exist_ok=True)

    original_filename = secure_filename(file.filename)
    temp_path = os.path.join(upload_dir, original_filename)
    file.save(temp_path)

    final_filename = base_name + '.mp4'
    final_path = os.path.join(upload_dir, final_filename)
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-i', temp_path,
        '-c:v', 'libx264', '-c:a', 'aac', final_path
    ]
    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError:
        flash('Video conversion to MP4 failed.', 'danger')
        os.remove(temp_path)
        return redirect(url_for('teacher.mark_attendance'))

    # cleanup temp and commit
    os.remove(temp_path)
    db.session.commit()

    flash('Attendance marked and video saved successfully!', 'success')
    return redirect(url_for('teacher.mark_attendance'))
    
@teacher_bp.route('/dashboard')
def dashboard():
    user = session.get('user')
    if not user or user.get('role') != 'teacher':
        return redirect(url_for('index.login'))

    return render_template('mark_attendance.html', teacher_name=user.get('name'))

@teacher_bp.route('/invoice', methods=['GET', 'POST'])
@login_required
def generate_invoice():
    user = session.get('user')
    teacher = Teacher.query.filter_by(email=user.get('email')).first()
    if not teacher:
        flash('Teacher not found', 'danger')
        return redirect(url_for('teacher.mark_attendance'))

    if request.method == 'GET':
        # months dropdown
        months = [
            ('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
            ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
            ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
        ]
        return render_template('invoice_select.html', months=months, now=datetime.now)

    # POST
    month = request.form.get('month')  # '01'-'12'
    year = request.form.get('year')    # '2025', etc

    # Get all marked attendance records for this teacher in selected month
    attendance_records = Attendance.query.join(Timetable).filter(
        Attendance.is_present == True,
        db.extract('month', Attendance.date) == int(month),
        db.extract('year', Attendance.date) == int(year),
        or_(
            Timetable.teacher_id == teacher.id,
            Attendance.proxy_id == teacher.id
        )
    ).order_by(Attendance.date).all()

    # Create entries list with all necessary information
    entries = []
    for record in attendance_records:
        entries.append({
            'date': record.date,
            'subject': record.timetable.subject,
            'grade': record.timetable.grade,
            'start_time': record.timetable.start_time,
            'is_proxy': record.is_proxy
        })

    total_lectures = len(entries)
    total_amount = total_lectures * teacher.pay_per_lecture

    # render HTML
    rendered = render_template('invoice_template.html',
        teacher=teacher,
        entries=entries,
        total_lectures=total_lectures,
        total_amount=total_amount,
        month=month,
        year=year
    )

    # create temp files
    tmp_html = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    tmp_html.write(rendered.encode('utf-8'))
    tmp_html.flush()

    # convert to PDF via wkhtmltopdf
    subprocess.run([
        'wkhtmltopdf', tmp_html.name, tmp_pdf.name
    ], check=True)

    # send and cleanup
    pdf_path = tmp_pdf.name
    tmp_html.close()
    tmp_pdf.close()
    return send_file(pdf_path,
                     as_attachment=True,
                     download_name=f"invoice_{teacher.id}_{year}{month}.pdf")

@teacher_bp.route('/invoice_template')
def invoice_template():
    teacher = Teacher.query.get(1)
    # POST
    month = "01"  # '01'-'12'
    year = "2025"    # '2025', etc
    # fetch all marked lectures for this teacher in selected month
    entries = Timetable.query.filter(
        Timetable.is_present == True,
        db.extract('month', Timetable.date) == int(month),
        db.extract('year', Timetable.date) == int(year),
        or_(
            Timetable.teacher_id == 1,
            Timetable.proxy_id == 1
        )
    ).order_by(Timetable.date).all()

    total_lectures = len(entries)
    total_amount = total_lectures * teacher.pay_per_lecture
    return render_template('invoice_template.html',
        teacher=teacher,
        entries=entries,
        total_lectures=total_lectures,
        total_amount=total_amount,
        month=month,
        year=year
    )