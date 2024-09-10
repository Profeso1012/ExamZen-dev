from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms import SelectField, IntegerField, DateField, TimeField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, ValidationError
from examzen.models import User, Organization


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    age = IntegerField('Age', validators=[DataRequired(),
            NumberRange(min=2, max=100, message='Age must be a number between 2 and 100')])
    status = SelectField('Status', choices=[('student', 'Student'), ('examiner', 'Examiner')], validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

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
    num_questions = IntegerField('Number of Questions (max 10)', validators=[DataRequired(), NumberRange(min=1, max=10)])
    num_options = IntegerField('Number of Options per Question', validators=[DataRequired(), NumberRange(min=2, max=10)])
    num_students = IntegerField('Number of Students (max 15)', validators=[DataRequired(), NumberRange(min=1, max=15)])
    exam_date = DateField('Exam Date (YYYY-MM-DD)', format='%Y-%m-%d', validators=[DataRequired()])
    exam_time = TimeField('Exam Time (HH:MM)', format='%H:%M', validators=[DataRequired()])
    duration = IntegerField('Duration (minutes, max 30)', validators=[DataRequired(), NumberRange(min=1, max=30)])
    is_private = BooleanField('Private Exam')
    student_usernames = SelectMultipleField('Select Students', choices=[], coerce=int)
    submit = SubmitField('Create Exam')

    def validate_examname(self, name):
        exam_name = Exam.query.filter_by(name=name.data).first()
        if user:
            raise ValidationError('That exam name is taken. Please choose a different one.')

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

    def validate_email(self, email):
        org = Organization.query.filter_by(email=email.data).first()
        if org:
            raise ValidationError('That email is already in use. Please choose a different one.')