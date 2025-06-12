from flask import Blueprint, render_template, session, redirect, url_for

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    # Check if user is logged in by looking for session data
    user = session.get('user')
    
    if user:
        role = user.get('role')
        
        if role == 'admin':
            # For admin users, check their level
            level = user.get('level')
            if level == 1:
                return redirect(url_for('admin.create_sales'))
            elif level == 2:
                return redirect(url_for('sales.dashboard'))
            else:
                # Fallback to general admin dashboard
                return redirect(url_for('admin.create_sales'))
        
        elif role == 'teacher':
            return redirect(url_for('teacher.mark_attendance'))
    
    # If no valid session or role found, redirect to login
    return redirect(url_for('index.login'))

@index_bp.route('/login')
def login():
    return render_template('login.html')

@index_bp.route('/signup')
def signup():
    return render_template('signup.html')

@index_bp.route('/fee-entry')
def fee_entry():
    return render_template('fee_entry.html')

