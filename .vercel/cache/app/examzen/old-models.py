from datetime import datetime
from examzen import db, app, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum('Student', 'Examiner'), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    profile_pic = db.Column(db.String(20), nullable=False, default='default.jpg')

    answers = db.relationship('Answer', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.status}')"


class Exam(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    num_questions = db.Column(db.Integer, nullable=False)
    num_options = db.Column(db.Integer, nullable=False)
    num_students = db.Column(db.Integer, nullable=False)
    exam_date = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    created_by = db.relationship('User', backref=db.backref('exams', lazy=True))
    exam_codes = db.relationship('ExamCode', backref='exam', lazy=True)
    answers = db.relationship('Answer', backref='exam', lazy=True)

    def __repr__(self):
        return f"Exam('{self.name}', '{self.exam_date}', '{self.created_by}')"


class Question(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id')) 
    question_text = db.Column(db.String(500), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    exam = db.relationship('Exam', backref=db.backref('questions', lazy=True))
    options = db.relationship('Examoption', backref='question', lazy=True)
    answers = db.relationship('Answer', backref='question', lazy=True)

    def __repr__(self):
        return f"Question('{self.question_text}', '{self.exam}')"


class Examoption(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    option_text = db.Column(db.String(200), nullable=False)
    option_letter = db.Column(db.String(1), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f"Examoption('{self.option_text}', '{self.option_letter}')"


class ExamCode(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    code = db.Column(db.String(10), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref='exam_codes', lazy=True)

    def __repr__(self):
        return f"ExamCode('{self.code}', '{self.user}')"


class Answer(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    answer = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"Answer('{self.answer}', '{self.is_correct}')"

# Create tables
with app.app_context():
    db.create_all()

#----------------------------------------

from flask_wtf import FlaskForm
from wtforms import StringField, RadioField, FieldList, FormField
from wtforms.validators import DataRequired

class OptionForm(FlaskForm):
    option_text = StringField('Option', validators=[DataRequired()])

class QuestionForm(FlaskForm):
    question_text = StringField('Question', validators=[DataRequired()])
    options = FieldList(FormField(OptionForm), min_entries=2, max_entries=6)
    correct_option = RadioField('Correct Option', choices=[], validators=[DataRequired()])

@app.route("/add_question/<int:exam_id>", methods=['GET', 'POST'])
@login_required
def add_question(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    form = QuestionForm()
    form.correct_option.choices = [(str(i), f'Option {i+1}') for i in range(exam.num_options)]

    if form.validate_on_submit():
        question = Question(exam_id=exam_id, question_text=form.question_text.data)
        db.session.add(question)
        
        for i, option_form in enumerate(form.options):
            is_correct = (str(i) == form.correct_option.data)
            option = Examoption(question=question, option_text=option_form.option_text.data,
                                option_letter=chr(65 + i), is_correct=is_correct)
            db.session.add(option)
        
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('add_question', exam_id=exam_id))

    return render_template('add_question.html', form=form, exam=exam)


    
"""The database tables should be created without issues, and the foreign key relationships should work as expected. However, I do have a few suggestions to improve the code:
In the User model, consider adding a unique constraint to the email column to ensure email addresses are unique.
In the Exam model, consider adding a check constraint to the duration column to ensure the duration is a positive integer.
In the Question model, consider adding a check constraint to the question_number column to ensure the question number is a positive integer.
In the Examoption model, consider adding a check constraint to the option_letter column to ensure the option letter is one of the expected values (e.g., 'A', 'B', 'C', 'D').
As for the foreign key relationships, they look correct. However, I recommend adding ondelete and onupdate arguments to the foreign key constraints to specify the desired behavior when a related record is deleted or updated.
For example, in the Answer model, you could add ondelete='CASCADE' to the foreign key constraint for the exam_id column, like this:
Python
exam_id = db.Column(db.Integer, db.ForeignKey('exam.id', ondelete='CASCADE'))
This would ensure that when an exam is deleted, all related answers are also deleted.
Overall, the code looks good, and with a few minor adjustments, it should work as expected."""