import os
import secrets
import uuid
from PIL import Image
from datetime import datetime
from flask import render_template, url_for, flash, redirect, request, jsonify
from examzen import app, db, bcrypt
from examzen.forms import RegistrationForm, LoginForm, UpdateAccountForm, ExamForm, OrganizationRegistrationForm
from examzen.models import User, Exam, TakenExam, Question, Examoption, ExamCode, Answer
from flask_login import login_user, current_user, logout_user, login_required


@app.template_filter('strftime')
def format_datetime(value, format='%Y-%m-%d %H:%M'):
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

@app.route("/")
@app.route("/home")
def home():
    if current_user and current_user.is_authenticated:
        if current_user.status == 'Student':
            # Get exams that the student is registered for
            public_exams = Exam.query.filter_by(is_private=False).all()
            registered_exams = Exam.query.join(ExamCode).filter(ExamCode.user_id == current_user.id).all()
            all_exams = list(set(public_exams + registered_exams))  # Remove duplicates           
            upcoming_exams = []
            taken_exams = TakenExam.query.filter_by(user_id=current_user.id).all()          
            taken_exam_ids = [exam.exam_id for exam in taken_exams]  # Get exam IDs from taken_exams
            taken_exams = Exam.query.filter(Exam.id.in_(taken_exam_ids)).all()  # Get exams from Exam table
            
            # Remove duplicates from taken_exams
            taken_exams = list(set(taken_exams))
            
            for exam in all_exams:
                if exam not in taken_exams:  # Check if exam is not already in taken_exams
                    answers = Answer.query.filter_by(exam_id=exam.id, user_id=current_user.id).first()
                    if answers:
                        taken_exams.append(exam)
                    else:
                        upcoming_exams.append(exam)           
            return render_template('home_student.html', upcoming_exams=upcoming_exams, taken_exams=taken_exams)

        elif current_user.status == 'Examiner':
            user_exams = list(set(Exam.query.filter_by(created_by_id=current_user.id).all()))  # Remove duplicates
            exams = user_exams[:2]  # Get the first two exams
            sample_exams = [
                Exam(id=1, name="Sample-math Exam", exam_date="2023-09-15", num_students=30),
                Exam(id=2, name="Sample-science Exam", exam_date="2023-09-20", num_students=25)
            ]
            exams += [exam for exam in sample_exams if exam not in exams][:2 - len(exams)]  # Add sample exams to fill the remaining slots
            return render_template('home_examiner.html', exams=exams)

        else:
            # Handle unknown status
            return "Unknown status", 400
    
    # Default home page for non-logged-in users
    return render_template('home.html')


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    forms = RegistrationForm()
    if forms.validate_on_submit():
        hash_pwd = bcrypt.generate_password_hash(forms.password.data).decode('utf-8')
        #status = forms.status.data
        new_user = User(
            username=forms.username.data,
            email=forms.email.data,
            age=forms.age.data,
            status=forms.status.data,
            password=hash_pwd
        )
        db.session.add(new_user)
        db.session.commit()
        flash(f'Account created for {forms.username.data}!, You can now log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=forms)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    forms = LoginForm()
    if forms.validate_on_submit():
        user = User.query.filter_by(email=forms.email.data).first()
        if user and bcrypt.check_password_hash(user.password, forms.password.data):
            login_user(user, remember=forms.remember.data)
            flash('You have been logged in!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=forms)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(5)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    forms = UpdateAccountForm()
    if forms.validate_on_submit():
        if forms.picture.data:
            picture_file = save_picture(forms.picture.data)
            current_user.profile_pic = picture_file
        current_user.username = forms.username.data
        current_user.email = forms.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        forms.username.data = current_user.username
        forms.email.data = current_user.email
    img_file = url_for('static', filename='profile_pics/' + current_user.profile_pic)
    return render_template('profile.html', title='Profile',
                            img_file=img_file, form=forms)


#mostly dummy routes

@app.route("/view_results")
@login_required
def view_results():
    return "Viewing results"

@app.route("/submit_complaint", methods=['GET', 'POST'])
@login_required
def submit_complaint():
    if request.method == 'POST':
        flash("Complaint submitted successfully!", "success")
    return render_template("submit_complaint.html")

@app.route('/create_exam', methods=['GET', 'POST'])
@login_required
def create_exam():
    form = ExamForm()
    # Populate student choices
    form.student_usernames.choices = [(user.id, user.username) for user in User.query.filter_by(status='Student').all()]

    if form.validate_on_submit():
        exam_datetime = datetime.combine(form.exam_date.data, form.exam_time.data)
        
        new_exam = Exam(
            name=form.name.data,
            num_questions=form.num_questions.data,
            num_options=form.num_options.data,
            num_students=form.num_students.data,
            exam_date=exam_datetime,
            duration=form.duration.data,
            created_by_id=current_user.id,
            is_private=form.is_private.data
        )
        db.session.add(new_exam)
        db.session.flush()  # This will populate the id of the new exam

        # Generate exam codes
        for _ in range(form.num_students.data):
            code = str(uuid.uuid4())[:7].upper()
            exam_code = ExamCode(exam_id=new_exam.id, code=code)
            db.session.add(exam_code)

        # If it's a private exam, assign codes to selected students
        if form.is_private.data:
            exam_codes = ExamCode.query.filter_by(exam_id=new_exam.id).all()
            for i, student_id in enumerate(form.student_usernames.data):
                if i < len(exam_codes):
                    exam_codes[i].user_id = student_id

        db.session.commit()

        flash('Exam created successfully! Please add questions.', 'success')
        return redirect(url_for('add_questions', exam_id=new_exam.id))

    return render_template('create_exam.html', form=form)


@app.route('/add_questions/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def add_questions(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if request.method == 'POST':
        question_text = request.form.get('question_text')
        question_number = request.form.get('question_number')
        options = request.form.getlist('option_text[]')
        correct_option = request.form.get('correct_option')

        new_question = Question(
            exam_id=exam.id,
            question_text=question_text,
            question_number=question_number
        )
        db.session.add(new_question)
        db.session.flush()

        for i, option_text in enumerate(options):
            new_option = Examoption(
                question_id=new_question.id,
                option_text=option_text,
                option_letter=chr(65 + i),
                is_correct=(str(i) == correct_option)
            )
            db.session.add(new_option)

        db.session.commit()

        if int(question_number) >= exam.num_questions:
            flash('All questions have been added. Exam creation complete!', 'success')
            return redirect(url_for('exam_dashboard'))

        if int(question_number) < exam.num_questions:
            flash('Question added successfully! Please add the next question.', 'success')
            return redirect(url_for('add_questions', exam_id=exam.id))
        elif int(question_number) >= exam.num_questions:
            flash('All questions have been added. Exam creation complete!', 'success')
            return redirect(url_for('exam_dashboard'))

        else:
            flash('If you see this, you might have an error!', 'failure')
            return redirect(url_for('exam_dashboard'))

    return render_template('add_questions.html', exam=exam, chr=chr)


@app.route('/exam_dashboard')
@login_required
def exam_dashboard():
    user_exams = Exam.query.filter_by(created_by_id=current_user.id).all()
    
    if current_user.status == 'Student':
        registered_exams = Exam.query.join(ExamCode).filter(ExamCode.user_id == current_user.id).all()
    else:
        registered_exams = []
    
    return render_template('exam_dashboard.html', user_exams=user_exams, registered_exams=registered_exams)

@app.route("/view_exam/<int:exam_id>")
@login_required
def view_exam(exam_id):
    return f"Viewing exam with ID: {exam_id}"

@app.route("/update_exam/<int:exam_id>", methods=['GET', 'POST'])
@login_required
def update_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if current_user.id != exam.created_by_id:
        abort(403)
    form = ExamForm()
    if form.validate_on_submit():
        exam.name = form.name.data
        exam.num_questions = form.num_questions.data
        exam.num_options = form.num_options.data
        exam.num_students = form.num_students.data
        exam.exam_date = form.exam_date.data
        exam.duration = form.duration.data
        exam.is_private = form.is_private.data
        db.session.commit()
        flash('Exam updated successfully!', 'success')
        return redirect(url_for('exam_dashboard'))
    elif request.method == 'GET':
        form.name.data = exam.name
        form.num_questions.data = exam.num_questions
        form.num_options.data = exam.num_options
        form.num_students.data = exam.num_students
        form.exam_date.data = exam.exam_date
        form.duration.data = exam.duration
        form.is_private.data = exam.is_private
    return render_template('update_exam.html', title='Update Exam', form=form, exam=exam)

@app.route('/delete_exam/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def delete_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if request.method == 'POST':
        # Delete all related relationships
        ExamCode.query.filter_by(exam_id=exam_id).delete()
        Answer.query.filter_by(exam_id=exam_id).delete()
        for question in Question.query.filter_by(exam_id=exam_id).all():
            Examoption.query.filter_by(question_id=question.id).delete()
        Question.query.filter_by(exam_id=exam_id).delete()
        # Remove exam from categories
        exam.categories = []
        # Delete the exam
        db.session.delete(exam)
        db.session.commit()
        flash('Exam deleted successfully!', 'success')
        return redirect(url_for('exam_dashboard'))
    return render_template('delete_exam.html', exam=exam)


#Student routes
@app.route("/take_exam/<int:exam_id>", methods=['GET', 'POST'])
@login_required
def take_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
    if request.method == 'POST':
        for question in questions:
            answer = request.form.get(f'question_{question.id}')
            correct_answer = next((option.option_text for option in question.options if option.is_correct), None)
            new_answer = Answer(
                exam_id=exam.id,
                question_id=question.id,
                user_id=current_user.id,
                answer=answer,
                is_correct=(answer == correct_answer)
            )
            db.session.add(new_answer)
        db.session.commit()
        # Delete the exam code
        ExamCode.query.filter_by(exam_id=exam_id, user_id=current_user.id).delete()
        taken_exam = TakenExam(exam_id=exam_id, user_id=current_user.id)
        db.session.add(taken_exam)
        db.session.commit()
        flash('Exam submitted successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('take_exam.html', exam=exam, questions=questions)

@app.route("/submit_exam/<int:exam_id>", methods=['POST'])
@login_required
def submit_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).all()
    
    correct_answers = 0
    total_questions = len(questions)
    
    for question in questions:
        answer = request.form.get(f'question_{question.id}')
        correct_option = Examoption.query.filter_by(question_id=question.id, is_correct=True).first()
        
        if answer and correct_option:
            is_correct = (answer == correct_option.option_letter)
            new_answer = Answer(exam_id=exam_id, question_id=question.id, user_id=current_user.id, 
                                answer=answer, is_correct=is_correct)
            db.session.add(new_answer)
            
            if is_correct:
                correct_answers += 1
    
    db.session.commit()
    
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    flash(f'Exam submitted successfully. Your score: {score:.2f}%', 'success')
    return redirect(url_for('home'))

@app.route("/view_exam_results/<int:exam_id>")
@login_required
def view_exam_results(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    # Ensure the user is a student
    if current_user.status != 'Student':
        abort(403)  # Forbidden access

    # Get all questions for this exam
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()

    # Get the student's answers for this exam
    answers = Answer.query.filter_by(exam_id=exam_id, user_id=current_user.id).all()

    # Ensure we have the same number of questions and answers
    if len(questions) != len(answers):
        flash('There was an issue retrieving your exam results. Please contact support.', 'danger')
        return redirect(url_for('submit_complaint'))

    # Calculate score
    total_questions = len(questions)
    correct_answers = sum(1 for answer in answers if answer.is_correct)
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

    # Prepare data for the chart
    score_data = [correct_answers, total_questions - correct_answers]

    # Get correct options for each question
    correct_options = {q.id: qo.option_text for q, qo in db.session.query(Question, Examoption).filter(
        Question.id == Examoption.question_id, Examoption.is_correct == True
    ).all()}

    # Zip questions and answers for easy iteration in the template
    question_answers = list(zip(questions, answers))

    return render_template('view_exam_results.html',
                           title='Exam Results',
                           exam=exam,
                           question_answers=question_answers,
                           score=score,
                           score_data=score_data,
                           correct_options=correct_options)


@app.route("/exam_statistics")
@login_required
def exam_statistics():
    return "Viewing exam statistics"

@app.route("/activity_log")
@login_required
def activity_log():
    return "Viewing activity log"

#Organization
@app.route("/register_organization", methods=['GET', 'POST'])
def register_organization():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = OrganizationRegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        organization = Organization(name=form.name.data, email=form.email.data, password=hashed_password)
        db.session.add(organization)
        db.session.commit()
        flash('Your organization account has been created! You can now log in', 'success')
        return redirect(url_for('login'))
    return render_template('register_organization.html', title='Register Organization', form=form)

@app.route("/create_organization", methods=['GET', 'POST'])
@login_required
def create_organization():
    if current_user.status != 'Organization':
        abort(403)
    form = OrganizationForm()
    if form.validate_on_submit():
        organization = Organization(name=form.name.data)
        db.session.add(organization)
        current_user.organization = organization
        db.session.commit()
        flash('Organization created successfully!', 'success')
        return redirect(url_for('organization_dashboard'))
    return render_template('create_organization.html', title='Create Organization', form=form)
    

@app.route("/organization_dashboard")
@login_required
def organization_dashboard():
    if current_user.status != 'Organization' or not current_user.organization:
        abort(403)
    return render_template('organization_dashboard.html', title='Organization Dashboard', organization=current_user.organization)

@app.route("/create_category", methods=['GET', 'POST'])
@login_required
def create_category():
    if current_user.status != 'Organization' or not current_user.organization:
        abort(403)
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data, organization=current_user.organization)
        db.session.add(category)
        db.session.commit()
        flash('Category created successfully!', 'success')
        return redirect(url_for('organization_dashboard'))
    return render_template('create_category.html', title='Create Category', form=form)

@app.route("/assign_user_to_category/<int:user_id>/<int:category_id>", methods=['POST'])
@login_required
def assign_user_to_category(user_id, category_id):
    if current_user.status != 'Organization' or not current_user.organization:
        abort(403)
    user = User.query.get_or_404(user_id)
    category = Category.query.get_or_404(category_id)
    if category.organization != current_user.organization:
        abort(403)
    category.users.append(user)
    db.session.commit()
    flash(f'{user.username} assigned to {category.name}', 'success')
    return redirect(url_for('organization_dashboard'))

@app.route("/assign_exam_to_category/<int:exam_id>/<int:category_id>", methods=['POST'])
@login_required
def assign_exam_to_category(exam_id, category_id):
    if current_user.status != 'Examiner':
        abort(403)
    exam = Exam.query.get_or_404(exam_id)
    category = Category.query.get_or_404(category_id)
    if exam.created_by_id != current_user.id:
        abort(403)
    exam.categories.append(category)
    db.session.commit()
    flash(f'{exam.name} assigned to {category.name}', 'success')
    return redirect(url_for('exam_dashboard'))

@app.route("/view_category_results/<int:category_id>")
@login_required
def view_category_results(category_id):
    if current_user.status != 'Examiner':
        abort(403)
    category = Category.query.get_or_404(category_id)
    exams = Exam.query.filter(Exam.categories.contains(category), Exam.created_by_id == current_user.id).all()
    results = {}
    for exam in exams:
        exam_results = Answer.query.filter(Answer.exam_id == exam.id, Answer.user_id.in_([user.id for user in category.users])).all()
        results[exam.id] = {
            'name': exam.name,
            'total_questions': len(exam.questions),
            'average_score': sum(answer.is_correct for answer in exam_results) / len(exam_results) * 100 if exam_results else 0
        }
    return render_template('view_category_results.html', title='Category Results', category=category, results=results)

