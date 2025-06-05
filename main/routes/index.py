from flask import Blueprint, render_template

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    return render_template('index.html')

@index_bp.route('/login')
def login():
    return render_template('login.html')

@index_bp.route('/fee-entry')
def fee_entry():
    return render_template('fee_entry.html')