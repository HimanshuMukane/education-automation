# routes_student.py

from flask import Blueprint, request, jsonify, render_template, send_file, abort
from datetime import datetime
from main.extensions import db
from main.models import Student, StudentInvoice

student_bp = Blueprint('student', __name__, url_prefix='/api')

@student_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'success': True, 'message': 'pong'})


@student_bp.route('/student/lookup', methods=['GET'])
def lookup_student():
    """
    Query params: grade=<string>&fname=<string>&lname=<string>
    Returns JSON:
      - If student exists:
        { "exists": true,
          "student_id": <int>,
          "total_fees": <float>,
          "fees_paid": <float>,
          "remaining_fee": <float>
        }
      - If not:
        { "exists": false }
    """
    grade = request.args.get('grade', '').strip()
    fname = request.args.get('fname', '').strip()
    lname = request.args.get('lname', '').strip()

    if not grade or not fname or not lname:
        return jsonify({'error': 'grade, fname, and lname are required'}), 400

    # Case-insensitive search for existing student
    student = (
        Student.query
        .filter(db.func.lower(Student.grade) == grade.lower())
        .filter(db.func.lower(Student.fname) == fname.lower())
        .filter(db.func.lower(Student.lname) == lname.lower())
        .first()
    )

    if not student:
        return jsonify({'exists': False})

    total_fees = student.total_fees
    fees_paid = student.fees_paid or 0.0
    remaining_fee = round(total_fees - fees_paid, 2)

    return jsonify({
        'exists': True,
        'student_id': student.id,
        'total_fees': total_fees,
        'fees_paid': fees_paid,
        'remaining_fee': remaining_fee
    })


@student_bp.route('/student/payment', methods=['POST'])
def record_payment():
    """
    Expects JSON payload:
    {
      "grade": "<string>",
      "fname": "<string>",
      "lname": "<string>",
      "total_fees": <float or null>,
      "payment_amount": <float>
    }

    Behavior:
      - If student exists: ignore total_fees in payload, only record new installment.
      - If student doesn't exist: total_fees must be provided (>0). Create Student, then record payment.
      - If payment_amount > remaining_fee, return error.
      - Update Student.fees_paid and insert a StudentInvoice row.
      - Return JSON with updated totals and full payment history.
    """
    data = request.get_json() or {}
    grade = (data.get('grade') or '').strip()
    fname = (data.get('fname') or '').strip()
    lname = (data.get('lname') or '').strip()
    total_fees_payload = data.get('total_fees')
    payment_amount = data.get('payment_amount')

    # Basic validation
    if not grade or not fname or not lname:
        return jsonify({'error': 'grade, fname, and lname are required'}), 400
    try:
        payment_amount = float(payment_amount)
    except (TypeError, ValueError):
        return jsonify({'error': 'payment_amount must be a number'}), 400
    if payment_amount <= 0:
        return jsonify({'error': 'payment_amount must be > 0'}), 400

    # Try to find existing student
    student = (
        Student.query
        .filter(db.func.lower(Student.grade) == grade.lower())
        .filter(db.func.lower(Student.fname) == fname.lower())
        .filter(db.func.lower(Student.lname) == lname.lower())
        .first()
    )

    # If not found, create new student (total_fees is required)
    if not student:
        if total_fees_payload is None:
            return jsonify({'error': 'total_fees required for a new student'}), 400
        try:
            total_fees = float(total_fees_payload)
        except (TypeError, ValueError):
            return jsonify({'error': 'total_fees must be a number'}), 400
        if total_fees <= 0:
            return jsonify({'error': 'total_fees must be > 0'}), 400

        student = Student(
            grade=grade,
            fname=fname,
            lname=lname,
            total_fees=total_fees,
            fees_paid=0.0
        )
        db.session.add(student)
        db.session.flush()  # to get student.id

    # Now student exists; compute remaining
    total_fees = float(student.total_fees)
    fees_paid_so_far = float(student.fees_paid or 0.0)
    remaining_before = round(total_fees - fees_paid_so_far, 2)

    if payment_amount > remaining_before:
        return jsonify({'error': 'Payment exceeds remaining fee'}), 400

    # Create a new StudentInvoice
    invoice = StudentInvoice(
        student_id=student.id,
        date=datetime.utcnow().date(),
        fees_paid=payment_amount,
        total_fees=total_fees
    )
    db.session.add(invoice)

    # Update student's cumulative fees_paid
    student.fees_paid = fees_paid_so_far + payment_amount

    db.session.commit()

    # Recompute after insertion
    fees_paid_new = float(student.fees_paid or 0.0)
    remaining_new = round(total_fees - fees_paid_new, 2)

    # Build full payment history (descending by date)
    payments = (
        StudentInvoice.query
        .filter_by(student_id=student.id)
        .order_by(StudentInvoice.date.desc(), StudentInvoice.id.desc())
        .all()
    )
    payments_list = [
        {
            'amount_paid': float(p.fees_paid),
            'date_paid': p.date.isoformat()
        }
        for p in payments
    ]

    return jsonify({
        'status': 'success',
        'student_id': student.id,
        'total_fees': total_fees,
        'fees_paid': fees_paid_new,
        'remaining_fee': remaining_new,
        'payments': payments_list
    })