import os
import subprocess
import tempfile

from datetime import datetime
from flask import Blueprint, request, session, current_app, render_template, redirect, url_for, flash, send_file
from sqlalchemy import or_

from werkzeug.utils import secure_filename

from main.extensions import db
from main.models import Timetable, Teacher
from main.utils import login_required

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

# Allowed video extensions
def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    return '.' in filename and ext in current_app.config.get('ALLOWED_EXTENSIONS', {'mp4','mov','avi','mkv'})

@teacher_bp.route('/mark-attendance', methods=['GET'])
@login_required
def mark_attendance():
    user = session.get('user')
    if not user or user.get('role') != 'teacher':
        return redirect(url_for('index.login'))

    # show all lectures where attendance not yet marked
    pending = Timetable.query.filter_by(is_present=False)
    pending = pending.order_by(Timetable.date.asc(), Timetable.start_time.asc()).all()
    return render_template('mark_attendance.html', lectures=pending)

@teacher_bp.route('/mark-attendance', methods=['POST'])
@login_required
def handle_attendance_upload():
    user = session.get('user')
    teacher = Teacher.query.filter_by(email=user.get('email')).first()
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('teacher.mark_attendance'))

    entry_id = request.form.get('entry_id')
    file = request.files.get('video')
    if not entry_id or not file or not allowed_file(file.filename):
        flash('Invalid lecture selection or file type. Only videos allowed.', 'danger')
        return redirect(url_for('teacher.mark_attendance'))

    entry = Timetable.query.get(entry_id)
    if not entry or entry.is_present:
        flash('Lecture not found or already marked.', 'danger')
        return redirect(url_for('teacher.mark_attendance'))

    # mark attendance and proxy if needed
    is_proxy = (entry.teacher_id != teacher.id)
    entry.is_present = True
    if is_proxy:
        entry.is_proxy = True
        entry.proxy_id = teacher.id

    # build folder name
    base_name = f"{entry.grade}_{entry.subject}_{entry.date.isoformat()}_{entry.teacher_id}_{entry.start_time.strftime('%H%M')}"
    prefix = 'proxy_' if is_proxy else ''
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], prefix + base_name)
    os.makedirs(upload_dir, exist_ok=True)

    # save temp file
    original_filename = secure_filename(file.filename)
    temp_path = os.path.join(upload_dir, original_filename)
    file.save(temp_path)

    # convert to mp4
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

    return render_template('teacher_dashboard.html', teacher_name=user.get('name'))

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
    # fetch all marked lectures for this teacher in selected month
    entries = Timetable.query.filter(
        Timetable.is_present == True,
        db.extract('month', Timetable.date) == int(month),
        db.extract('year', Timetable.date) == int(year),
        or_(
            Timetable.teacher_id == teacher.id,
            Timetable.proxy_id == teacher.id
        )
    ).order_by(Timetable.date).all()

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
