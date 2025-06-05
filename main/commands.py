from flask.cli import with_appcontext
import click
from main.models import Admin, Teacher
from main.extensions import db
from main.utils import generate_password_hash

@click.command('rehash-passwords')
@with_appcontext
def rehash_passwords():
    """Rehash all passwords using bcrypt."""
    click.echo('Rehashing passwords...')
    
    # Rehash admin passwords
    admins = Admin.query.all()
    for admin in admins:
        if not admin.password.startswith('$2b$'):  # Check if not already a bcrypt hash
            click.echo(f'Rehashing password for admin: {admin.email}')
            admin.password = generate_password_hash('admin123')  # Set a temporary password
    
    # Rehash teacher passwords
    teachers = Teacher.query.all()
    for teacher in teachers:
        if not teacher.password.startswith('$2b$'):  # Check if not already a bcrypt hash
            click.echo(f'Rehashing password for teacher: {teacher.email}')
            teacher.password = generate_password_hash('teacher123')  # Set a temporary password
    
    db.session.commit()
    click.echo('All passwords have been rehashed. Default passwords set: admin123 for admins, teacher123 for teachers')
    click.echo('Please ask users to change their passwords on next login.')

def init_app(app):
    """Register CLI commands."""
    app.cli.add_command(rehash_passwords) 