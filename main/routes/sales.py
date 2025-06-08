from flask import Blueprint, render_template, request, jsonify, session, url_for, current_app, make_response
from main.models import Student, StudentInvoice
from main.utils import util_db_add, util_db_update, util_db_delete, login_required, is_admin
from datetime import date
import pdfkit

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

@sales_bp.route('/dashboard')
@login_required
@is_admin(2)
def dashboard():
    invoices = (
        StudentInvoice.query
        .join(Student, Student.id == StudentInvoice.student_id)
        .add_columns(
            StudentInvoice.id,
            Student.grade,
            Student.fname, Student.lname,
            StudentInvoice.total_fees,
            StudentInvoice.fees_paid,
            StudentInvoice.date
        )
        .order_by(StudentInvoice.id.desc())
        .all()
    )
    return render_template('sales_dashboard.html',
                           invoices=invoices,
                           current_date=date.today().isoformat())

@sales_bp.route('/fee')
@login_required
@is_admin(2)
def lookup_fee():
    grade = request.args.get('grade','').strip()
    name  = request.args.get('name','').strip()
    if not grade or not name:
        return jsonify({'success': False, 'error': 'Grade and name are required'}), 400

    parts = name.split(None,1)
    fname = parts[0]
    lname = parts[1] if len(parts)>1 else ''

    student = Student.query.filter_by(grade=grade, fname=fname, lname=lname).first()
    if not student:
        return jsonify({'success': False, 'new': True}), 200

    return jsonify({'success': True, 'total_fees': student.total_fees}), 200


@sales_bp.route('/invoice/<int:inv_id>')
@login_required
@is_admin(2)
def download_invoice(inv_id):
    inv = StudentInvoice.query.get_or_404(inv_id)
    student = inv.student  # via backref
    # Reuse the same breakdown logic from record_payment:
    pct = {
        'tuition': 0.82, 'books': 0.04, 'ebook': 0.02,
        'kit': 0.02, 'uniform': 0.04, 'bag': 0.03, 'activity': 0.03
    }
    try:
        gnum = int(student.grade)
    except:
        gnum = None
    if gnum and 9 <= gnum <= 12:
        pct['ebook'] = 0.04
        pct['kit']   = 0.00
    breakdown = { k: round(student.total_fees * v, 2) for k,v in pct.items() }

    html = render_template('invoice.html',
                           student=student,
                           invoice=inv,
                           breakdown=breakdown)
    pdf = pdfkit.from_string(html, False, options=current_app.config.get('WKHTMLTOPDF_OPTIONS', {}))
    response = make_response(pdf)
    response.headers.update({
        'Content-Type': 'application/pdf',
        'Content-Disposition': f'attachment; filename=invoice_{inv.id}.pdf'
    })
    return response

@sales_bp.route('/record/<int:inv_id>', methods=['DELETE'])
@login_required
@is_admin(2)
def delete_record(inv_id):
    inv = StudentInvoice.query.get(inv_id)
    if not inv:
        return jsonify({'success': False, 'error': 'Invoice not found'}), 404

    # roll back the student’s paid total
    inv.student.fees_paid -= inv.fees_paid

    # delete the invoice
    result = util_db_delete(inv)
    if not result.get('success'):
        return jsonify({'success': False, 'error': result.get('error')}), 500

    return jsonify({'success': True, 'message': result.get('message')}), 200


# ── EDIT existing invoice’s fees_paid ─────────────────────────────────────────
@sales_bp.route('/record/<int:inv_id>', methods=['PUT'])
@login_required
@is_admin(2)
def edit_record(inv_id):
    data = request.get_json()
    new_paid = data.get('fees_paid')
    try:
        new_paid = float(new_paid)
        if new_paid < 0:
            raise ValueError()
    except:
        return jsonify({'success': False, 'error': 'Invalid amount'}), 400

    inv = StudentInvoice.query.get(inv_id)
    if not inv:
        return jsonify({'success': False, 'error': 'Invoice not found'}), 404

    # adjust student.fees_paid by the difference
    diff = new_paid - inv.fees_paid
    inv.student.fees_paid += diff
    inv.fees_paid = new_paid

    result = util_db_update()
    if not result.get('success'):
        return jsonify({'success': False, 'error': result.get('error')}), 500

    return jsonify({'success': True, 'new_paid': new_paid}), 200

@sales_bp.route('/record', methods=['POST'])
@login_required
@is_admin(2)
def record_payment():
    data = request.get_json()
    grade = data.get('grade','').strip()
    name  = data.get('name','').strip()
    paid_raw = data.get('fees_paid')
    total_raw = data.get('total_fees')

    if not grade or not name or paid_raw is None or total_raw is None:
        return jsonify({'success': False, 'error': 'All fields are required'}), 400

    try:
        paid = float(paid_raw)
        total = float(total_raw)
        if paid < 0 or total < 0:
            raise ValueError()
    except:
        return jsonify({'success': False, 'error': 'Invalid numbers provided'}), 400

    parts = name.split(None,1)
    fname = parts[0]
    lname = parts[1] if len(parts)>1 else ''

    # find or create student
    student = Student.query.filter_by(grade=grade, fname=fname, lname=lname).first()
    if not student:
        student = Student(
            grade=grade,
            fname=fname,
            lname=lname,
            total_fees=total,
            fees_paid=0.0
        )
        util_db_add(student)
    else:
        # update total_fees if changed
        if abs(student.total_fees - total) > 0.01:
            student.total_fees = total

    # update or create invoice
    inv = StudentInvoice.query.filter_by(student_id=student.id).first()
    if inv:
        inv.fees_paid += paid
    else:
        inv = StudentInvoice(
            student_id=student.id,
            date=date.today(),
            total_fees=total,
            fees_paid=paid
        )
        util_db_add(inv)

    # sync Student.fees_paid
    student.fees_paid += paid

    result = util_db_update()
    if not result.get('success'):
        return jsonify({'success': False, 'error': 'Database update failed'}), 500

    # percentage breakdown logic (same as before)
    pct = {
        'tuition': 0.82,
        'books':   0.04,
        'ebook':   0.02,
        'kit':     0.02,
        'uniform': 0.04,
        'bag':     0.03,
        'activity':0.03
    }
    try:
        gnum = int(grade)
    except:
        gnum = None
    if gnum and 9 <= gnum <= 12:
        pct['ebook'] = 0.04
        pct['kit']   = 0.00

    breakdown = { k: round(total * v, 2) for k,v in pct.items() }
    html = render_template('invoice.html', student=student, invoice=inv, breakdown=breakdown)
    pdf = pdfkit.from_string(html, False, options=current_app.config.get('WKHTMLTOPDF_OPTIONS', {}))

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=invoice.pdf'
    return response