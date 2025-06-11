from main.extensions import db
from datetime import datetime, time

class BaseModel(db.Model):
    __abstract__ = True

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            col_name = column.name
            value = getattr(self, col_name)

            # Skip password field by name
            if col_name == 'password':
                continue

            # Handle datetime
            if isinstance(value, datetime):
                result[col_name] = value.isoformat()

            # Handle time
            elif isinstance(value, time):
                result[col_name] = value.strftime('%H:%M:%S')

            # Handle JSON/dict fields (e.g., bank_info)
            elif isinstance(value, dict):
                result[col_name] = value

            else:
                result[col_name] = value

        return result

class Admin(BaseModel):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    level = db.Column(db.Integer, nullable=False, default=2)
    is_active = db.Column(db.Boolean, default=True, index=True)

    def __repr__(self):
        return f"<Admin {self.name}>"


class Teacher(BaseModel):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    bank_info = db.Column(db.JSON, nullable=True)
    pay_per_lecture = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True, index=True)

    timetable_entries = db.relationship('Timetable', foreign_keys='Timetable.teacher_id', backref='assigned_teacher', lazy='dynamic')
    invoices = db.relationship('TeacherInvoice', backref='teacher', lazy='dynamic')

    def __repr__(self):
        return f"<Teacher {self.name}>"


class Student(BaseModel):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(100), nullable=False)
    lname = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(20), nullable=False, index=True)
    total_fees = db.Column(db.Float, nullable=False)
    fees_paid = db.Column(db.Float, default=0.0)

    invoices = db.relationship('StudentInvoice', backref='student', lazy='dynamic')

    def __repr__(self):
        return f"<Student {self.fname} {self.lname}>"


class Timetable(BaseModel):
    __tablename__ = 'timetable_templates'

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False, index=True)
    day_of_week = db.Column(db.Integer, nullable=False, index=True)  # 0-6 for Monday-Sunday
    start_time = db.Column(db.Time, nullable=False)
    grade = db.Column(db.String(20), nullable=False, index=True)

    attendances = db.relationship('Attendance', backref='timetable', lazy='dynamic')

    def __repr__(self):
        return f"<Timetable {self.subject} {self.day_of_week}>"


class TeacherInvoice(BaseModel):
    __tablename__ = 'teacher_invoices'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    total_lectures = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<TeacherInvoice {self.teacher_id} {self.date}>"


class StudentInvoice(BaseModel):
    __tablename__ = 'student_invoices'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    fees_paid = db.Column(db.Float, nullable=False)
    total_fees = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<StudentInvoice {self.student_id} {self.date}>"


class Attendance(BaseModel):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable_templates.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    is_present = db.Column(db.Boolean, default=False)
    is_proxy = db.Column(db.Boolean, default=False)
    proxy_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True, index=True)

    proxy_teacher = db.relationship('Teacher', foreign_keys=[proxy_id])

    def __repr__(self):
        return f"<Attendance {self.date} {self.timetable.subject}>"
