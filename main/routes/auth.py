from flask import Blueprint, render_template, redirect, url_for, request 

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/test', methods=['GET', 'POST'])
def test():
    return "Auth Working"