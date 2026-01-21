from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, HiddenField, TextAreaField
from wtforms import SelectField, IntegerField, DateField, TimeField, SelectMultipleField, DateTimeLocalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, ValidationError, Optional
from examzen.models import User, Organization, Class, Exam


class RegistrationForm(FlaskForm):
    registration_type = HiddenField('Registration Type', default='individual')  # 'individual' or 'organization'
    
    # Individual Fields
    username = StringField('Username') # Custom validation manually or conditionally
    age = IntegerField('Age', validators=[NumberRange(min=2, max=100, message='Age must be a number between 2 and 100'), Optional()])
    status = SelectField('Status', choices=[('Student', 'Student'), ('Examiner', 'Examiner')], validators=[Optional()]) # Optional if org
    
    # Organization Fields
    organization_name = StringField('Organization Name')
    
    # Common Fields
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        if self.registration_type.data == 'individual':
            if not username.data or len(username.data) < 4 or len(username.data) > 20:
                 raise ValidationError('Username must be between 4 and 20 characters.')
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_organization_name(self, organization_name):
        if self.registration_type.data == 'organization':
            if not organization_name.data or len(organization_name.data) < 2:
                raise ValidationError('Organization name must be at least 2 characters.')
            org = Organization.query.filter_by(name=organization_name.data).first()
            if org:
                raise ValidationError('That organization name is already taken.')

    def validate_email(self, email):
        # Check User table for duplicates
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')
        # Also check Organization table just in case, though we primarily create a User for the Org Admin
        # But wait, the previous code had a separate Organization table email. 
        # We will unify: Org Admin is a User. 


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')


class ExamForm(FlaskForm):
    name = StringField('Exam Name', validators=[DataRequired(), Length(min=1, max=100)])
    num_questions = IntegerField('Number of Questions', validators=[DataRequired(), NumberRange(min=1, max=200)])
    num_options = IntegerField('Number of Options per Question', validators=[DataRequired(), NumberRange(min=2, max=10)])
    num_students = IntegerField('Number of Students', validators=[DataRequired(), NumberRange(min=1, max=1000)])
    start_time = DateTimeLocalField('Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeLocalField('End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    duration = IntegerField('Duration (minutes)', validators=[DataRequired(), NumberRange(min=5, max=180)])
    is_private = BooleanField('Private Exam (Invite Only)')
    student_usernames = SelectMultipleField('Select Students', choices=[], coerce=int)
    submit = SubmitField('Create Exam')

class OrganizationRegistrationForm(FlaskForm):
    name = StringField('Organization Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register Organization')

    def validate_name(self, name):
        org = Organization.query.filter_by(name=name.data).first()
        if org:
            raise ValidationError('That organization name is already taken. Please choose a different one.')

        if org:
            raise ValidationError('That email is already in use. Please choose a different one.')

class ClassForm(FlaskForm):
    name = StringField('Class Name', validators=[DataRequired(), Length(min=2, max=100)])
    code = StringField('Class Code', validators=[DataRequired(), Length(min=3, max=20)])
    submit = SubmitField('Create Class')
    students_file = FileField('Upload Students (Excel/CSV)', validators=[FileAllowed(['xlsx', 'xls', 'csv'], 'Excel or CSV only!')])
    manual_emails = TextAreaField('Manual Emails (Comma or Newline separated)')

    
    def validate_code(self, code):
        cl = Class.query.filter_by(code=code.data).first()
        if cl:
            raise ValidationError('That class code is already taken.')

class ExcelUploadForm(FlaskForm):
    file = FileField('Upload Excel File', validators=[DataRequired(), FileAllowed(['xlsx', 'xls'])])
    submit = SubmitField('Upload')