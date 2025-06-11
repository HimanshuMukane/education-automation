from flask import Blueprint, render_template, request, jsonify, session, url_for, current_app, make_response, redirect, flash, send_file
from main.models import Student, StudentInvoice, Admin, Sales
from main.utils import util_db_add, util_db_update, util_db_delete, login_required, is_sales
from datetime import date, datetime
import pdfkit
import os
import subprocess
import tempfile

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

@sales_bp.route('/dashboard')
@login_required
@is_sales
def dashboard():
    # Get the current sales admin
    current_admin = Sales.query.filter_by(email=session['user']['email']).first()
    if not current_admin:
        return redirect(url_for('index.login'))

    invoices = (
        StudentInvoice.query
        .join(Student, Student.id == StudentInvoice.student_id)
        .add_columns(
            StudentInvoice.id,
            Student.grade,
            Student.fname, Student.lname,
            StudentInvoice.total_fees,
            StudentInvoice.fees_paid,
            StudentInvoice.date,
            StudentInvoice.created_by
        )
        .order_by(StudentInvoice.id.desc())
        .all()
    )
    return render_template('sales_dashboard.html',
                           invoices=invoices,
                           current_date=date.today().isoformat(),
                           sales_person=current_admin.name)

@sales_bp.route('/fee')
@login_required
@is_sales
def lookup_fee():
    try:
        grade = request.args.get('grade','').strip()
        name  = request.args.get('name','').strip()
        if not grade or not name:
            return jsonify({'success': False, 'error': 'Grade and name are required'}), 400

        parts = name.split(None,1)
        fname = parts[0]
        lname = parts[1] if len(parts)>1 else ''

        student = Student.query.filter_by(grade=grade, fname=fname, lname=lname).first()
        if not student:
            return jsonify({'success': False, 'new': True, 'error': None}), 200

        return jsonify({
            'success': True, 
            'total_fees': student.total_fees,
            'error': None
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'new': False
        }), 500

@sales_bp.route('/invoice/<int:inv_id>')
@login_required
@is_sales
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
@is_sales
def delete_record(inv_id):
    inv = StudentInvoice.query.get(inv_id)
    if not inv:
        return jsonify({'success': False, 'error': 'Invoice not found'}), 404

    # roll back the student's paid total
    inv.student.fees_paid -= inv.fees_paid

    # delete the invoice
    result = util_db_delete(inv)
    if not result.get('success'):
        return jsonify({'success': False, 'error': result.get('error')}), 500

    return jsonify({'success': True, 'message': result.get('message')}), 200

# ── EDIT existing invoice's fees_paid ─────────────────────────────────────────
@sales_bp.route('/record/<int:inv_id>', methods=['PUT'])
@login_required
@is_sales
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
@is_sales
def record_payment():
    try:
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

        # Get current sales person
        current_sales = Sales.query.filter_by(email=session['user']['email']).first()
        if not current_sales:
            return jsonify({'success': False, 'error': 'Sales person not found'}), 404

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

        # update or create invoice
        inv = StudentInvoice.query.filter_by(student_id=student.id).first()
        if inv:
            inv.fees_paid += paid
        else:
            inv = StudentInvoice(
                student_id=student.id,
                sales_id=current_sales.id,
                date=date.today(),
                total_fees=total,
                fees_paid=paid,
                created_by=current_sales.name
            )
            util_db_add(inv)

        # sync Student.fees_paid
        student.fees_paid += paid

        result = util_db_update()
        if not result.get('success'):
            return jsonify({'success': False, 'error': 'Database update failed'}), 500

        # percentage breakdown logic
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

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sales_bp.route('/generate-invoice', methods=['GET', 'POST'])
@login_required
def generate_invoice():
    user = session.get('user')
    if not user or user.get('role') != 'sales':
        return redirect(url_for('index.login'))

    sales = Sales.query.filter_by(email=user.get('email')).first()
    if not sales:
        flash('Sales profile not found.', 'danger')
        return redirect(url_for('index.login'))

    if request.method == 'POST':
        month = request.form.get('month')
        year = request.form.get('year')
        
        # Get all student invoices for the selected month and year
        start_date = date(int(year), int(month), 1)
        if int(month) == 12:
            end_date = date(int(year) + 1, 1, 1)
        else:
            end_date = date(int(year), int(month) + 1, 1)

        invoices = StudentInvoice.query.filter(
            StudentInvoice.sales_id == sales.id,
            StudentInvoice.date >= start_date,
            StudentInvoice.date < end_date
        ).all()

        # Calculate totals and prepare entries
        total_amount = 0
        entries = []
        for inv in invoices:
            student = inv.student
            commission = inv.fees_paid * (sales.commission_rate / 100)
            total_amount += inv.fees_paid
            
            entries.append({
                'date': inv.date,
                'student_name': f"{student.fname} {student.lname}",
                'grade': student.grade,
                'amount': inv.fees_paid,
                'commission': commission
            })

        total_commission = total_amount * (sales.commission_rate / 100)

        # Generate PDF
        html = render_template('sales_invoice_template.html',
                             sales=sales,
                             month=month,
                             year=year,
                             entries=entries,
                             total_amount=total_amount,
                             total_commission=total_commission,
                             commission_rate=sales.commission_rate)

        pdf = pdfkit.from_string(html, False, options=current_app.config.get('WKHTMLTOPDF_OPTIONS', {}))
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=sales_commission_{month}_{year}.pdf'
        return response

    # For GET request, show the form
    months = [
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ]
    
    return render_template('sales_invoice_select.html', 
                         months=months,
                         current_date=datetime.now())