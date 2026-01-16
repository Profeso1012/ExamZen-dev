import os
import secrets
import uuid
from PIL import Image
from datetime import datetime
from flask import render_template, url_for, flash, redirect, request, jsonify, abort
from examzen import app, db, bcrypt
from examzen.forms import RegistrationForm, LoginForm, UpdateAccountForm, ExamForm, OrganizationRegistrationForm, ClassForm, ExcelUploadForm
from examzen.models import User, Exam, TakenExam, Question, Examoption, ExamCode, Answer, Class, Notification
from examzen.utils import parse_questions_excel, parse_students_excel, send_notification
from flask_login import login_user, current_user, logout_user, login_required


@app.route('/proctor/log', methods=['POST'])
@login_required
def proctor_log():
    data = request.get_json()
    exam_id = data.get('exam_id')
    event_type = data.get('type')
    details = data.get('details', '')
    
    # In a real app, append to existing session or create one.
    # For now, we will just print to console or simplistic logging
    print(f"PROCTOR ALERT: User {current_user.username} in Exam {exam_id}: {event_type} - {details}")
    
    # Logic to fetch or create ProctorSession
    # session = ProctorSession.query.filter_by(user_id=current_user.id, exam_id=exam_id).first()
    # if session: ....
    
    return jsonify({'status': 'logged'})

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


@app.route("/account")
@login_required
def account():
    return render_template('account.html', title='Account')


def save_picture(form_picture):
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    
    # Get the MIME type
    mimetype = form_picture.content_type or 'image/jpeg'
    
    # Convert image to binary
    import io
    img_io = io.BytesIO()
    i.save(img_io, format='JPEG')
    img_io.seek(0)
    
    return img_io.getvalue(), 'image/jpeg'


@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    import base64
    forms = UpdateAccountForm()
    if forms.validate_on_submit():
        if forms.picture.data:
            picture_data, mimetype = save_picture(forms.picture.data)
            current_user.profile_pic = picture_data
            current_user.profile_pic_mimetype = mimetype
        current_user.username = forms.username.data
        current_user.email = forms.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        forms.username.data = current_user.username
        forms.email.data = current_user.email
    
    # Convert binary image to base64 data URI for display
    if current_user.profile_pic:
        pic_data = current_user.profile_pic
        # Handle memoryview from database
        if isinstance(pic_data, memoryview):
            pic_data = bytes(pic_data)
        
        mimetype = current_user.profile_pic_mimetype or 'image/jpeg'
        b64_pic = base64.b64encode(pic_data).decode('utf-8')
        img_file = f"data:{mimetype};base64,{b64_pic}"
    else:
        # Use default profile picture
        default_pic_path = os.path.join(app.root_path, 'static/profile_pics/default.jpg')
        if os.path.exists(default_pic_path):
            with open(default_pic_path, 'rb') as f:
                pic_data = f.read()
                b64_pic = base64.b64encode(pic_data).decode('utf-8')
                img_file = f"data:image/jpeg;base64,{b64_pic}"
        else:
            img_file = url_for('static', filename='profile_pics/default.jpg')
    
    return render_template('profile.html', title='Profile',
                            img_file=img_file, form=forms)


#mostly dummy routes



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
    # Populate student choices if no class selected, mostly kept for backwards compat or adhop
    form.student_usernames.choices = [(user.id, user.username) for user in User.query.filter_by(status='Student').all()]

    if form.validate_on_submit():
        new_exam = Exam(
            name=form.name.data,
            num_questions=form.num_questions.data,
            num_options=form.num_options.data,
            num_students=form.num_students.data,
            start_time=form.start_time.data, # Strict window
            end_time=form.end_time.data,
            exam_date=form.start_time.data.date(), # Fallback for listing
            duration=form.duration.data,
            created_by_id=current_user.id,
            is_private=form.is_private.data
        )
        db.session.add(new_exam)
        db.session.flush()

        # Generate codes if private
        if form.is_private.data:
            for _ in range(form.num_students.data):
                code = str(uuid.uuid4())[:7].upper()
                exam_code = ExamCode(exam_id=new_exam.id, code=code)
                db.session.add(exam_code)

        db.session.commit()
        flash('Exam created successfully! Please add questions.', 'success')
        return redirect(url_for('add_questions', exam_id=new_exam.id))

    return render_template('create_exam.html', form=form)


@app.route('/import/questions/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def import_questions(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by_id != current_user.id:
        abort(403)
        
    form = ExcelUploadForm()
    if form.validate_on_submit():
        if form.file.data:
            questions_data = parse_questions_excel(form.file.data)
            count = 0
            for i, q in enumerate(questions_data):
                new_q = Question(
                    exam_id=exam.id,
                    question_text=q['text'],
                    question_number=i + 1
                )
                db.session.add(new_q)
                db.session.flush()
                
                for opt in q['options']:
                    new_opt = Examoption(
                        question_id=new_q.id,
                        option_text=opt['text'],
                        option_letter=opt['letter'],
                        is_correct=opt['is_correct']
                    )
                    db.session.add(new_opt)
                count += 1
            
            db.session.commit()
            flash(f'Successfully imported {count} questions!', 'success')
            return redirect(url_for('exam_dashboard'))
            
    return render_template('import_questions.html', form=form, exam=exam)


# Class Management Routes
@app.route('/classes', methods=['GET', 'POST'])
@login_required
def classes():
    if current_user.status == 'Student':
        my_classes = current_user.enrolled_classes.all()
        return render_template('classes_student.html', classes=my_classes)
    else:
        # Teacher
        form = ClassForm()
        if form.validate_on_submit():
            new_class = Class(
                name=form.name.data,
                code=form.code.data,
                created_by_id=current_user.id
            )
            new_class.teachers.append(current_user)
            db.session.add(new_class)
            db.session.commit()
            flash('Class created successfully!', 'success')
            return redirect(url_for('classes'))
            
        my_classes = current_user.teaching_classes.all()
        return render_template('classes_teacher.html', classes=my_classes, form=form)

@app.route('/class/<int:class_id>', methods=['GET'])
@login_required
def view_class(class_id):
    classroom = Class.query.get_or_404(class_id)
    # Check access
    if current_user not in classroom.teachers and current_user not in classroom.students:
        abort(403)
        
    return render_template('view_class.html', classroom=classroom)



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

# Results & Analytics Routes

@app.route('/exam/results/<int:exam_id>', methods=['GET'])
@login_required
def view_results(exam_id):
    # Student specific result view
    exam = Exam.query.get_or_404(exam_id)
    taken_exam = TakenExam.query.filter_by(user_id=current_user.id, exam_id=exam_id).first()
    
    if not taken_exam:
        flash('You have not taken this exam yet.', 'warning')
        return redirect(url_for('take_exam', exam_id=exam_id))
        
    # Calculate score
    total_questions = len(exam.questions)
    correct_answers = Answer.query.filter_by(user_id=current_user.id, exam_id=exam_id, is_correct=True).count()
    score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    return render_template('view_results.html', exam=exam, score=score, correct=correct_answers, total=total_questions)

@app.route('/exam/analytics/<int:exam_id>', methods=['GET'])
@login_required
def exam_analytics(exam_id):
    # Teacher view of all students
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by_id != current_user.id:
        abort(403)
        
    taken_exams = TakenExam.query.filter_by(exam_id=exam_id).all()
    
    results = []
    for taken in taken_exams:
        user = User.query.get(taken.user_id)
        correct_count = Answer.query.filter_by(user_id=taken.user_id, exam_id=exam_id, is_correct=True).count()
        total_q = len(exam.questions)
        score_pct = (correct_count / total_q * 100) if total_q > 0 else 0
        
        results.append({
            'student': user,
            'score': score_pct,
            'correct': correct_count,
            'total': total_q,
            'date': taken.taken_at
        })
        
    return render_template('exam_analytics.html', exam=exam, results=results)



#Student routes
@app.route("/take_exam/<int:exam_id>", methods=['GET'])
@login_required
def take_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    # Check if already taken?
    existing = TakenExam.query.filter_by(user_id=current_user.id, exam_id=exam_id).first()
    if existing:
        flash('You have already taken this exam.', 'info')
        return redirect(url_for('view_results', exam_id=exam_id)) # Assuming view_results exists or needs creation

    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
    
    questions_json = []
    for q in questions:
        qdict = {
            'id': q.id,
            'question_number': q.question_number,
            'question_text': q.question_text,
            'options': []
        }
        for opt in q.options:
            qdict['options'].append({
                'id': opt.id,
                'option_text': opt.option_text,
                'option_letter': getattr(opt, 'option_letter', '')
            })
        questions_json.append(qdict)
    return render_template('take_exam.html', exam=exam, questions=questions, questions_json=questions_json)

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

    # If no answers found, redirect to home
    if not answers:
        flash('You have not taken this exam yet.', 'info')
        return redirect(url_for('home'))

    # Create a dictionary of answers by question_id for easier lookup
    answers_dict = {answer.question_id: answer for answer in answers}

    # Calculate score based on submitted answers only
    correct_answers = sum(1 for answer in answers if answer.is_correct)
    total_answers = len(answers)
    score = (correct_answers / total_answers) * 100 if total_answers > 0 else 0

    # Prepare data for the chart
    score_data = [correct_answers, total_answers - correct_answers]

    # Get correct options for each question that was answered
    correct_options = {}
    for question in questions:
        if question.id in answers_dict:
            correct_option = Examoption.query.filter_by(
                question_id=question.id, 
                is_correct=True
            ).first()
            if correct_option:
                correct_options[question.id] = correct_option.option_text

    # Zip answered questions and answers for easy iteration in the template
    answered_questions = [q for q in questions if q.id in answers_dict]
    question_answers = list(zip(answered_questions, [answers_dict[q.id] for q in answered_questions]))

    return render_template('view_exam_results.html',
                           title='Exam Results',
                           exam=exam,
                           question_answers=question_answers,
                           score=score,
                           score_data=score_data,
                           correct_options=correct_options)

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

