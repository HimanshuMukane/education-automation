from flask import Blueprint, render_template, session, redirect, url_for

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

@teacher_bp.route('/dashboard')
def dashboard():
    """
    Only Teachers (role="teacher") should see this page.
    Renders templates/teacher_dashboard.html
    """
    user = session.get('user')
    if not user or user.get('role') != 'teacher':
        return redirect(url_for('index.index'))

    return render_template('teacher_dashboard.html', teacher_name=user.get('name'))
