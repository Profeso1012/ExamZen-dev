from datetime import datetime
from examzen import db, app, login_manager
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import ENUM

# Enum for User status
status_enum = ENUM('Student', 'Examiner', 'Organization', name='status_enum', schema='public')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    age = db.Column(db.Integer, nullable=False)
    status = db.Column(status_enum, nullable=False)  # Named ENUM for PostgreSQL
    password = db.Column(db.String(255), nullable=False)
    profile_pic = db.Column(db.LargeBinary, nullable=True)  # Store image as binary data
    profile_pic_mimetype = db.Column(db.String(50), default='image/jpeg')  # Store image MIME type
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True)

    # Relationships
    answers = db.relationship('Answer', backref='user', lazy=True)
    exams_created = db.relationship('Exam', backref='creator', lazy=True)

    @property
    def profile_pic_base64(self):
        """Convert profile pic to base64 for display"""
        if self.profile_pic:
            import base64
            return base64.b64encode(self.profile_pic).decode('utf-8')
        return None

    def __repr__(self):
        return f"User('{self.username}', '{self.status}')"

# Organization model
class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    users = db.relationship('User', backref='organization', lazy=True)
    categories = db.relationship('Category', backref='organization', lazy=True)
    classes = db.relationship('Class', backref='org', lazy=True)

    def get_accepted_teachers(self):
        """Get all teachers who have accepted invitation to this organization"""
        from examzen.models import OrganizationTeacher, User
        accepted = OrganizationTeacher.query.filter_by(
            organization_id=self.id, 
            status='accepted'
        ).all()
        return [User.query.get(assoc.teacher_id) for assoc in accepted]
    
    def get_all_classes(self):
        """Get all classes accepted into this organization"""
        return Class.query.filter_by(organization_id=self.id).all()

    def __repr__(self):
        return f"Organization('{self.name}')"

# Category model
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)

    # Relationships
    users = db.relationship('User', secondary='user_categories', backref='categories', lazy='dynamic')

    def __repr__(self):
        return f"Category('{self.name}')"

# Association table for User and Category (many-to-many)
user_categories = db.Table('user_categories',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

# Association tables for Classes
student_classes = db.Table('student_classes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('class.id'), primary_key=True)
)

teacher_classes = db.Table('teacher_classes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('class.id'), primary_key=True)
)

# Class Model
class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    students = db.relationship('User', secondary=student_classes, backref='enrolled_classes', lazy='dynamic')
    teachers = db.relationship('User', secondary=teacher_classes, backref='teaching_classes', lazy='dynamic')
    exams = db.relationship('Exam', backref='assigned_class', lazy=True)
    invitations = db.relationship('ClassInvitation', backref='classroom', lazy='dynamic',
                                  cascade='all, delete-orphan')

    def __repr__(self):
        return f"Class('{self.name}', '{self.code}')"


# Student class invitation (teacher invites student → student accepts/rejects)
class ClassInvitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invited_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)

    student = db.relationship('User', foreign_keys=[student_id], backref='class_invitations')
    invited_by = db.relationship('User', foreign_keys=[invited_by_id])

    def __repr__(self):
        return f"ClassInvitation(class={self.class_id}, student={self.student_id}, status={self.status})"


# Teacher submits class to an organization for the org to accept/manage
class OrgClassRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)

    classroom = db.relationship('Class', backref='org_requests')
    organization = db.relationship('Organization', backref='class_requests')
    teacher = db.relationship('User', backref='submitted_class_requests')

    def __repr__(self):
        return f"OrgClassRequest(class={self.class_id}, org={self.organization_id}, status={self.status})"

# Notification Model
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50), default='general')  # general, invitation, complaint, exam_assigned
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Additional fields for invitations and complaints
    related_id = db.Column(db.Integer, nullable=True)  # Can be organization_id, exam_id, etc.
    action_taken = db.Column(db.Boolean, default=False)  # For tracking if invitation accepted/rejected
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_notifications')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='notifications')

    def __repr__(self):
        return f"Notification('{self.type}', '{self.message[:30]}...')"

# OrganizationTeacher Association Model (for tracking invitations)
class OrganizationTeacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    invited_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)
    
    organization = db.relationship('Organization', backref='teacher_associations')
    teacher = db.relationship('User', backref='organization_associations')
    
    def __repr__(self):
        return f"OrgTeacher(Org:{self.organization_id}, Teacher:{self.teacher_id}, Status:{self.status})"

# ProctorSession Model
class ProctorSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'))
    events = db.Column(db.Text, nullable=True) # JSON string
    flags = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Exam model
class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    num_questions = db.Column(db.Integer, nullable=False)
    num_options = db.Column(db.Integer, nullable=False)
    num_students = db.Column(db.Integer, nullable=False)
    exam_date = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    is_private = db.Column(db.Boolean, default=False)
    start_time = db.Column(db.DateTime, nullable=True) # Strict start window
    end_time = db.Column(db.DateTime, nullable=True)   # Strict end window
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)

    # Relationships
    questions = db.relationship('Question', backref='exam', lazy=True, cascade="all, delete-orphan", order_by="Question.question_number")
    exam_codes = db.relationship('ExamCode', backref='exam', lazy=True, cascade="all, delete-orphan")
    answers = db.relationship('Answer', backref='exam', lazy=True, cascade="all, delete-orphan")
    categories = db.relationship('Category', secondary='exam_categories', backref='exams', lazy='dynamic')

    def __repr__(self):
        return f"Exam('{self.name}', '{self.exam_date}', '{self.creator.username}')"

# Association table for Exam and Category (many-to-many)
exam_categories = db.Table('exam_categories',
    db.Column('exam_id', db.Integer, db.ForeignKey('exam.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

# TakenExam model
class TakenExam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    exam = db.relationship('Exam', backref='taken_exams', lazy=True)
    user = db.relationship('User', backref='taken_exams', lazy=True)

# Question model
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id')) 
    question_text = db.Column(db.String(500), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    options = db.relationship('Examoption', backref='question', lazy=True, cascade="all, delete-orphan")
    answers = db.relationship('Answer', backref='question', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"Question('{self.question_text}', '{self.exam.name}')"

# ExamOption model
class Examoption(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    option_text = db.Column(db.String(200), nullable=False)
    option_letter = db.Column(db.String(1), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"Examoption('{self.option_text}', '{self.option_letter}')"

# ExamCode model
class ExamCode(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    code = db.Column(db.String(10), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='exam_codes', lazy=True)

    def __repr__(self):
        return f"ExamCode('{self.code}', '{self.user.username}')"

# Answer model
class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    answer = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"Answer('{self.answer}', '{self.is_correct}')"

# Create tables (drop existing ones first)
with app.app_context():
    #db.drop_all() Temporarily drop all tables
    db.create_all()  # Recreate tables
