import os
import secrets
import uuid
from PIL import Image
from datetime import datetime, timedelta
from flask import render_template, url_for, flash, redirect, request, jsonify, abort
from examzen import app, db, bcrypt
from examzen.forms import RegistrationForm, LoginForm, UpdateAccountForm, ExamForm, OrganizationRegistrationForm, ClassForm, ExcelUploadForm
from examzen.models import User, Exam, TakenExam, Question, Examoption, ExamCode, Answer, Class, Notification, Organization, OrganizationTeacher
from examzen.utils import parse_questions_excel, parse_students_excel, send_notification
from flask_login import login_user, current_user, logout_user, login_required


@app.route("/org/create_class", methods=['GET', 'POST'])
@login_required
def org_create_class():
    if current_user.status != 'Organization' or not current_user.organization_id:
        abort(403)
        
    if request.method == 'POST':
        class_name = request.form.get('class_name')
        class_code = request.form.get('class_code')
        
        # Check if class code exists
        if Class.query.filter_by(code=class_code).first():
            flash('This class code is already in use.', 'danger')
            return redirect(url_for('org_create_class'))
            
        new_class = Class(
            name=class_name,
            code=class_code,
            organization_id=current_user.organization_id,
            created_by_id=current_user.id
        )
        db.session.add(new_class)
        db.session.flush() # Get the class ID
        
        all_members = [] # List of (email, role)
        
        # 1. Manual Entry
        emails = request.form.getlist('emails[]')
        roles = request.form.getlist('roles[]')
        for e, r in zip(emails, roles):
            if e and e.strip():
                all_members.append((e.strip().lower(), r))
                
        # 2. CSV Upload
        if 'members_csv' in request.files:
            file = request.files['members_csv']
            if file and file.filename.endswith('.csv'):
                try:
                    df = pd.read_csv(file)
                    df.columns = [c.strip().lower() for c in df.columns]
                    # Support multiple column names for flexibility
                    email_col = next((c for c in df.columns if 'email' in c), None)
                    role_col = next((c for c in df.columns if 'role' in c or 'status' in c), None)
                    
                    if email_col and role_col:
                        for _, row in df.iterrows():
                            e = str(row[email_col]).strip().lower()
                            r = str(row[role_col]).strip().title()
                            if r not in ['Student', 'Teacher', 'Examiner']:
                                r = 'Student' # Default
                            if r == 'Teacher': r = 'Examiner' # Map 'Teacher' to 'Examiner' status if needed, 
                                                              # though User model has 'Examiner'. 
                                                              # Status enum is: 'Student', 'Examiner', 'Organization'
                            all_members.append((e, r))
                except Exception as ex:
                    flash(f'Error parsing CSV: {ex}', 'warning')
                    
        # Process Members
        added_count = 0
        for email, role in all_members:
            user = User.query.filter_by(email=email).first()
            if not user:
                # Create user
                username = email.split('@')[0]
                # Handle username collision
                if User.query.filter_by(username=username).first():
                    username = f"{username}_{secrets.token_hex(2)}"
                
                hashed_password = bcrypt.generate_password_hash('Student123').decode('utf-8')
                user = User(
                    username=username,
                    email=email,
                    age=18,
                    status=role if role in ['Student', 'Examiner'] else 'Student',
                    password=hashed_password,
                    organization_id=current_user.organization_id
                )
                db.session.add(user)
                db.session.flush()
                
            # Assign to class
            if role == 'Examiner' or role == 'Teacher':
                if user not in new_class.teachers:
                    new_class.teachers.append(user)
                    added_count += 1
            else:
                if user not in new_class.students:
                    new_class.students.append(user)
                    added_count += 1
                    
        db.session.commit()
        flash(f'Class "{class_name}" created with {added_count} members.', 'success')
        return redirect(url_for('organization_dashboard'))
        
    return render_template('org_create_class.html')

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
        # Redirect authenticated users to their dashboard.
        # This unifies the experience and avoids using old 'home_student.html' or 'home_examiner.html'
        # which might contain bugs or legacy code. The 'dashboard' route handles
        # the logic for rendering the correct dashboard based on user status.
        return redirect(url_for('dashboard'))
    
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
        
        if forms.registration_type.data == 'organization':
            # create org
            new_org = Organization(name=forms.organization_name.data)
            db.session.add(new_org)
            db.session.flush() # get ID
            
            # create admin user
            new_user = User(
                username=forms.organization_name.data, # using org name as username for now as discussed
                email=forms.email.data,
                age=0, # Not applicable
                status='Organization',
                password=hash_pwd,
                organization_id=new_org.id
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'Organization account created for {forms.organization_name.data}! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        else:
            # Individual
            new_user = User(
                username=forms.username.data,
                email=forms.email.data,
                age=forms.age.data,
                status=forms.status.data,
                password=hash_pwd
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'Account created for {forms.username.data}! You can now log in', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html', title='Register', form=forms)


@app.route("/forgot_password", methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    # Using LoginForm structure but effectively just for email
    # A dedicated ForgotPasswordForm would be better but for now we can just use HTML form or reuse LoginForm if we ignore password
    # Actually, let's just make a simple GET/POST here with loose coupling
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Logic to send email would go here
            flash('An email has been sent with instructions to reset your password.', 'info')
        else:
            # Security: Don't reveal if user exists? Or maybe do for this level of app? 
            # Standard practice is to say "If an account exists..." but user might want explicit
             flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
        
    return render_template('forgot_password.html', title='Forgot Password')


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
        # Get class_id from request if provided
        class_id = request.form.get('class_id')
        
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
            is_private=form.is_private.data,
            class_id=int(class_id) if class_id and class_id.isdigit() else None
        )
        db.session.add(new_exam)
        db.session.flush()

        # Handle Private Exam Recipients
        if form.is_private.data:
            recipient_users = set()
            
            # 1. Class-based recipients
            if class_id and class_id.isdigit():
                classroom = Class.query.get(int(class_id))
                if classroom and current_user in classroom.teachers:
                    for student in classroom.students:
                        recipient_users.add(student)
            
            # 2. File upload
            if 'recipients_file' in request.files:
                file = request.files['recipients_file']
                if file and file.filename:
                    file_emails = parse_students_excel(file)
                    for email in file_emails:
                        user = User.query.filter_by(email=email.strip().lower()).first()
                        if not user:
                            # Auto-create student
                            username = email.split('@')[0]
                            if User.query.filter_by(username=username).first():
                                username = f"{username}{secrets.randbelow(9999)}"
                            
                            hashed_pwd = bcrypt.generate_password_hash('Student123').decode('utf-8')
                            user = User(
                                username=username,
                                email=email.strip().lower(),
                                status='Student',
                                age=18,
                                password=hashed_pwd,
                                organization_id=current_user.organization_id
                            )
                            db.session.add(user)
                            db.session.flush()
                        recipient_users.add(user)
            
            # 3. Manual emails
            manual_text = request.form.get('manual_recipients', '')
            if manual_text:
                manual_list = manual_text.replace('\n', ',').split(',')
                for email in manual_list:
                    if email.strip():
                        user = User.query.filter_by(email=email.strip().lower()).first()
                        if not user:
                            # Auto-create student
                            username = email.split('@')[0]
                            if User.query.filter_by(username=username).first():
                                username = f"{username}{secrets.randbelow(9999)}"
                            
                            hashed_pwd = bcrypt.generate_password_hash('Student123').decode('utf-8')
                            user = User(
                                username=username,
                                email=email.strip().lower(),
                                status='Student',
                                age=18,
                                password=hashed_pwd,
                                organization_id=current_user.organization_id
                            )
                            db.session.add(user)
                            db.session.flush()
                        recipient_users.add(user)
            
            # Generate ExamCodes for all recipients
            for user in recipient_users:
                code = str(uuid.uuid4())[:7].upper()
                exam_code = ExamCode(exam_id=new_exam.id, code=code, user_id=user.id)
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
            return redirect(url_for('manage_exam', exam_id=exam.id))
            
    return render_template('import_questions.html', form=form, exam=exam)


# Class Management Routes
@app.route('/classes', methods=['GET', 'POST'])
@login_required
def classes():
    if current_user.status == 'Student':
        # Removed .all() as relationships might be mapped as lists or queries. 
        # Error indicated 'InstrumentedList' so it's already a list.
        my_classes = current_user.enrolled_classes
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
            # Add Teachers
            new_class.teachers.append(current_user)
            db.session.add(new_class)
            db.session.flush() # Get ID

            # Process Students
            added_count = 0
            created_count = 0
            all_emails = set()

            # 1. Excel/CSV
            if form.students_file.data:
                file_emails = parse_students_excel(form.students_file.data)
                for e in file_emails:
                    all_emails.add(e.strip().lower())

            # 2. Manual Emails
            if form.manual_emails.data:
                manual_list = form.manual_emails.data.replace('\n', ',').split(',')
                for e in manual_list:
                    if e.strip():
                        all_emails.add(e.strip().lower())

            # 3. Provision/Link
            for email in all_emails:
                user = User.query.filter_by(email=email).first()
                if not user:
                    # Create new student account
                    username = email.split('@')[0]
                    # Simple duplicate username checker
                    if User.query.filter_by(username=username).first():
                        username = f"{username}{secrets.randbelow(9999)}"
                    
                    hashed_pwd = bcrypt.generate_password_hash('Student123').decode('utf-8')
                    user = User(
                        username=username,
                        email=email,
                        status='Student',
                        age=18, # Default
                        password=hashed_pwd,
                        organization_id=current_user.organization_id # Inherit Org if applicable
                    )
                    db.session.add(user)
                    created_count += 1
                
                # Add to class if not already
                if user not in new_class.students:
                    new_class.students.append(user)
                    added_count += 1

            db.session.commit()
            
            msg = 'Class created successfully!'
            if added_count > 0:
                msg += f' Added {added_count} students ({created_count} new accounts).'
            flash(msg, 'success')
            return redirect(url_for('classes'))
            
        my_classes = current_user.teaching_classes
        return render_template('classes_teacher.html', classes=my_classes, form=form)

@app.route('/classes/student')
@login_required
def classes_student():
    """Separate route for students to view their classes"""
    if current_user.status != 'Student':
        return redirect(url_for('classes'))
    my_classes = current_user.enrolled_classes
    return render_template('classes_student.html', classes=my_classes)

@app.route('/class/<int:class_id>', methods=['GET', 'POST'])
@login_required
def view_class(class_id):
    classroom = Class.query.get_or_404(class_id)
    # Check access
    if current_user not in classroom.teachers and current_user not in classroom.students:
        abort(403)
    
    # Handle POST - Add Students
    if request.method == 'POST' and current_user in classroom.teachers:
        added_count = 0
        created_count = 0
        all_emails = set()

        # 1. Excel/CSV
        if 'students_file' in request.files:
            file = request.files['students_file']
            if file and file.filename:
                file_emails = parse_students_excel(file)
                for e in file_emails:
                    all_emails.add(e.strip().lower())

        # 2. Manual Emails
        manual_text = request.form.get('manual_emails', '')
        if manual_text:
            manual_list = manual_text.replace('\n', ',').split(',')
            for e in manual_list:
                if e.strip():
                    all_emails.add(e.strip().lower())

        # 3. Provision/Link
        for email in all_emails:
            user = User.query.filter_by(email=email).first()
            if not user:
                # Create new student account
                username = email.split('@')[0]
                # Simple duplicate username checker
                if User.query.filter_by(username=username).first():
                    username = f"{username}{secrets.randbelow(9999)}"
                
                hashed_pwd = bcrypt.generate_password_hash('Student123').decode('utf-8')
                user = User(
                    username=username,
                    email=email,
                    status='Student',
                    age=18, # Default
                    password=hashed_pwd,
                    organization_id=current_user.organization_id # Inherit Org if applicable
                )
                db.session.add(user)
                created_count += 1
            
            # Add to class if not already
            if user not in classroom.students:
                classroom.students.append(user)
                added_count += 1

        db.session.commit()
        
        msg = f'Added {added_count} students ({created_count} new accounts).' if added_count > 0 else 'No new students added.'
        flash(msg, 'success')
        return redirect(url_for('view_class', class_id=class_id))
        
    return render_template('view_class.html', classroom=classroom)



@app.route('/add_questions/<int:exam_id>', methods=['GET', 'POST'])
@app.route('/add_questions/<int:exam_id>/<int:q_idx>', methods=['GET', 'POST'])
@login_required
def add_questions(exam_id, q_idx=None):
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by_id != current_user.id:
        abort(403)
        
    # Get existing questions for this exam
    questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.question_number).all()
    
    # If no q_idx provided, default to the next one to be added
    if q_idx is None:
        q_idx = len(questions) + 1
        
    # Boundary check
    if q_idx < 1: q_idx = 1
    if q_idx > exam.num_questions:
        flash('You have reached the limit of questions for this exam.', 'info')
        return redirect(url_for('manage_exam', exam_id=exam.id))

    # Find if this question already exists (for editing during flow)
    existing_q = next((q for q in questions if q.question_number == q_idx), None)

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        options_texts = request.form.getlist('option_text[]')
        correct_option_idx = request.form.get('correct_option')
        direction = request.form.get('direction', 'next') # 'next' or 'prev' or 'finish'

        if existing_q:
            # Update existing
            existing_q.question_text = question_text
            # Clear and re-add options for simplicity or update them
            for opt in existing_q.options:
                db.session.delete(opt)
            db.session.flush()
        else:
            # Create new
            existing_q = Question(
                exam_id=exam.id,
                question_text=question_text,
                question_number=q_idx
            )
            db.session.add(existing_q)
            db.session.flush()

        for i, opt_text in enumerate(options_texts):
            new_option = Examoption(
                question_id=existing_q.id,
                option_text=opt_text,
                option_letter=chr(65 + i),
                is_correct=(str(i) == correct_option_idx)
            )
            db.session.add(new_option)

        db.session.commit()

        if direction == 'prev' and q_idx > 1:
            return redirect(url_for('add_questions', exam_id=exam.id, q_idx=q_idx-1))
        elif direction == 'next':
            if q_idx < exam.num_questions:
                return redirect(url_for('add_questions', exam_id=exam.id, q_idx=q_idx+1))
            else:
                flash('Final question saved.', 'success')
                return redirect(url_for('manage_exam', exam_id=exam.id))
        else:
            return redirect(url_for('manage_exam', exam_id=exam.id))

    return render_template('add_questions.html', exam=exam, q_idx=q_idx, existing_q=existing_q, chr=chr)


@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_single_question(question_id):
    question = Question.query.get_or_404(question_id)
    exam = question.exam
    if exam.created_by_id != current_user.id:
        abort(403)
        
    # Lock check: Prevent editing if anyone has already taken the exam
    if TakenExam.query.filter_by(exam_id=exam.id).first():
        flash('Editing is locked because students have already started or submitted this exam.', 'danger')
        return redirect(url_for('manage_exam', exam_id=exam.id))
        
    if request.method == 'POST':
        question.question_text = request.form.get('question_text')
        options_texts = request.form.getlist('option_text[]')
        correct_option_idx = request.form.get('correct_option')

        # Update options
        for i, opt in enumerate(question.options):
            if i < len(options_texts):
                opt.option_text = options_texts[i]
                opt.is_correct = (str(i) == correct_option_idx)
        
        # If there are NEW options (unlikely given fixed num_options but good for robustness)
        if len(options_texts) > len(question.options):
            for i in range(len(question.options), len(options_texts)):
                new_opt = Examoption(
                    question_id=question.id,
                    option_text=options_texts[i],
                    option_letter=chr(65 + i),
                    is_correct=(str(i) == correct_option_idx)
                )
                db.session.add(new_opt)

        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('manage_exam', exam_id=exam.id))

    return render_template('edit_single_question.html', question=question, exam=exam, chr=chr)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.status == 'Student':
        # Get exams logic (copied/adapted from home)
        public_exams = Exam.query.filter_by(is_private=False).all()
        registered_exams = Exam.query.join(ExamCode).filter(ExamCode.user_id == current_user.id).all()
        all_exams = list(set(public_exams + registered_exams))
        
        upcoming_exams = []
        taken_exams_list = []
        
        # Get IDs of taken exams
        taken_entries = TakenExam.query.filter_by(user_id=current_user.id).all()
        taken_ids = [t.exam_id for t in taken_entries]
        
        for exam in all_exams:
            if exam.id in taken_ids:
                taken_exams_list.append(exam)
            else:
                upcoming_exams.append(exam)
                
        return render_template('student_dashboard.html', upcoming_exams=upcoming_exams, taken_exams=taken_exams_list)
        
    elif current_user.status == 'Examiner':
        # Fetch data for examiner dashboard
        exams = Exam.query.filter_by(created_by_id=current_user.id).order_by(Exam.created_at.desc()).limit(5).all()
        notifications = Notification.query.filter_by(receiver_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
        
        # Chart Data Calculation
        all_user_exams = Exam.query.filter_by(created_by_id=current_user.id).all()
        exam_names = []
        avg_scores = []
        student_counts_taken = []
        
        for exam in all_user_exams:
            taken_count = TakenExam.query.filter_by(exam_id=exam.id).count()
            
            if taken_count > 0:
                total_score_sum = 0
                taken_entries = TakenExam.query.filter_by(exam_id=exam.id).all()
                for entry in taken_entries:
                     correct_answers = Answer.query.filter_by(user_id=entry.user_id, exam_id=exam.id, is_correct=True).count()
                     total_questions = len(exam.questions)
                     if total_questions > 0:
                         score = (correct_answers / total_questions) * 100
                         total_score_sum += score
                
                avg_score = total_score_sum / taken_count
            else:
                avg_score = 0
            
            if taken_count > 0 or len(all_user_exams) <= 10:
                 exam_names.append(exam.name)
                 avg_scores.append(round(avg_score, 1))
                 student_counts_taken.append(taken_count)
        
        # Limit to last 10
        exam_names = exam_names[-10:]
        avg_scores = avg_scores[-10:]
        student_counts_taken = student_counts_taken[-10:]

        return render_template('examiner_dashboard.html', 
                               exams=exams, 
                               notifications=notifications, 
                               now=datetime.utcnow(),
                               exam_names=exam_names,
                               avg_scores=avg_scores,
                               student_counts=student_counts_taken)
    elif current_user.status == 'Organization':
        return render_template('org_admin_dashboard.html')
    else:
        return redirect(url_for('home'))

@app.route('/my-exams')
@login_required
def my_exams():
    if current_user.status != 'Examiner':
        abort(403)
    exams = Exam.query.filter_by(created_by_id=current_user.id).order_by(Exam.created_at.desc()).all()
    return render_template('my_exams.html', exams=exams, now=datetime.utcnow())

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html')

@app.route('/organizations')
@login_required
def organizations():
    return render_template('organizations.html')

@app.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    if request.method == 'POST' and current_user.status == 'Examiner':
        title = request.form.get('title')
        message = request.form.get('message')
        recipient_type = request.form.get('recipient_type') # 'student' or 'class'
        
        if recipient_type == 'class':
            class_id = request.form.get('class_id')
            classroom = Class.query.filter_by(id=class_id).first()
            if classroom and classroom.creator_id == current_user.id: # Ensure ownership
                 count = 0
                 for student in classroom.students:
                     notif = Notification(title=title, message=message, receiver_id=student.id)
                     db.session.add(notif)
                     count += 1
                 db.session.commit()
                 flash(f'Notification sent to {count} students in {classroom.name}!', 'success')
            else:
                 # Check if teacher is just a teacher, not creator? usually creator is main owner. 
                 # But model might be Many-to-Many 'teachers'.
                 # Let's check: Class.teachers relationship.
                 if classroom and current_user in classroom.teachers:
                     count = 0
                     for student in classroom.students:
                         notif = Notification(title=title, message=message, receiver_id=student.id)
                         db.session.add(notif)
                         count += 1
                     db.session.commit()
                     flash(f'Notification sent to {count} students in {classroom.name}!', 'success')
                 else:
                     flash('Class not found or access denied.', 'danger')
                     
        else: # Individual student
            recipient_username = request.form.get('recipient')
            if recipient_username:
                user = User.query.filter_by(username=recipient_username).first()
                if user:
                    notif = Notification(title=title, message=message, receiver_id=user.id)
                    db.session.add(notif)
                    db.session.commit()
                    flash(f'Notification sent to {recipient_username}!', 'success')
                else:
                    flash('User not found.', 'danger')
            else:
                flash('Recipient username required.', 'warning')
            
        return redirect(url_for('notifications'))

    user_notifications = Notification.query.filter_by(receiver_id=current_user.id).order_by(Notification.created_at.desc()).all()
    # Pass classes for the dropdown
    my_classes = []
    if current_user.status == 'Examiner':
        my_classes = current_user.teaching_classes
        
    return render_template('notifications.html', notifications=user_notifications, classes=my_classes)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

# Organization-Teacher Invitation Routes
@app.route('/org/invite_teacher', methods=['POST'])
@login_required
def org_invite_teacher():
    """Organization invites a teacher"""
    if current_user.status != 'Organization':
        abort(403)
    
    from examzen.models import OrganizationTeacher
    teacher_email = request.form.get('teacher_email')
    teacher = User.query.filter_by(email=teacher_email, status='Examiner').first()
    
    if not teacher:
        flash('Teacher not found. Please ensure they have an Examiner account.', 'danger')
        return redirect(url_for('organization_dashboard'))
    
    # Check if already invited
    existing = OrganizationTeacher.query.filter_by(
        organization_id=current_user.organization_id,
        teacher_id=teacher.id
    ).first()
    
    if existing:
        flash('This teacher has already been invited.', 'warning')
        return redirect(url_for('organization_dashboard'))
    
    # Create invitation
    invitation = OrganizationTeacher(
        organization_id=current_user.organization_id,
        teacher_id=teacher.id,
        status='pending'
    )
    db.session.add(invitation)
    
    # Send notification
    notif = Notification(
        sender_id=current_user.id,
        receiver_id=teacher.id,
        message=f'{current_user.organization.name} has invited you to join their organization. Accept to share your classes with them.',
        type='invitation',
        related_id=current_user.organization_id
    )
    db.session.add(notif)
    db.session.commit()
    
    flash(f'Invitation sent to {teacher.username}!', 'success')
    return redirect(url_for('organization_dashboard'))

@app.route('/teacher/respond_invitation/<int:notification_id>/<action>')
@login_required
def respond_invitation(notification_id, action):
    """Teacher accepts or rejects organization invitation"""
    if current_user.status != 'Examiner':
        abort(403)
    
    from examzen.models import OrganizationTeacher
    notif = Notification.query.get_or_404(notification_id)
    
    if notif.receiver_id != current_user.id or notif.type != 'invitation':
        abort(403)
    
    invitation = OrganizationTeacher.query.filter_by(
        organization_id=notif.related_id,
        teacher_id=current_user.id
    ).first()
    
    if not invitation:
        flash('Invitation not found.', 'danger')
        return redirect(url_for('notifications'))
    
    if action == 'accept':
        invitation.status = 'accepted'
        invitation.responded_at = datetime.utcnow()
        notif.action_taken = True
        flash('You have accepted the invitation!', 'success')
    elif action == 'reject':
        invitation.status = 'rejected'
        invitation.responded_at = datetime.utcnow()
        notif.action_taken = True
        flash('You have rejected the invitation.', 'info')
    
    db.session.commit()
    return redirect(url_for('notifications'))

# Complaint System
@app.route('/exam/<int:exam_id>/complaint', methods=['POST'])
@login_required
def submit_exam_complaint(exam_id):
    """Student submits complaint about exam result"""
    if current_user.status != 'Student':
        abort(403)
    
    exam = Exam.query.get_or_404(exam_id)
    complaint_message = request.form.get('complaint_message')
    
    if not complaint_message:
        flash('Please provide a complaint message.', 'warning')
        return redirect(url_for('view_exam_results', exam_id=exam_id))
    
    # Send notification to exam creator
    notif = Notification(
        sender_id=current_user.id,
        receiver_id=exam.created_by_id,
        message=f'Complaint from {current_user.username} about exam "{exam.name}": {complaint_message}',
        type='complaint',
        related_id=exam_id
    )
    db.session.add(notif)
    db.session.commit()
    
    flash('Your complaint has been sent to the teacher.', 'success')
    return redirect(url_for('view_exam_results', exam_id=exam_id))

@app.route('/notification/<int:notif_id>/mark_read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    """Mark notification as read"""
    notif = Notification.query.get_or_404(notif_id)
    if notif.receiver_id != current_user.id:
        abort(403)
    notif.is_read = True
    db.session.commit()
    return jsonify({'status': 'success'})



@app.route('/available_exams')
@login_required
def available_exams():
    return render_template('available_exams.html')

@app.route('/my_results')
@login_required
def my_results():
    """Student views all their exam results"""
    if current_user.status != 'Student':
        abort(403)
    
    # Get all exams the student has taken
    taken_exams = TakenExam.query.filter_by(user_id=current_user.id).order_by(TakenExam.taken_at.desc()).all()
    
    results = []
    for taken in taken_exams:
        exam = taken.exam
        # Calculate score
        total_questions = len(exam.questions)
        correct_answers = Answer.query.filter_by(
            exam_id=exam.id,
            user_id=current_user.id,
            is_correct=True
        ).count()
        
        score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        results.append({
            'exam': exam,
            'taken_at': taken.taken_at,
            'score': round(score, 2),
            'correct': correct_answers,
            'total': total_questions
        })
    
    return render_template('my_results.html', results=results)


@app.route('/exam/<int:exam_id>/manage')
@login_required
def manage_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by_id != current_user.id:
        abort(403)
    return render_template('exam_management.html', exam=exam, now=datetime.utcnow())

@app.route('/exam/<int:exam_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if current_user.id != exam.created_by_id:
        abort(403)
    form = ExamForm()
    if form.validate_on_submit():
        exam.name = form.name.data
        exam.num_questions = form.num_questions.data
        exam.num_options = form.num_options.data
        exam.num_students = form.num_students.data
        exam.exam_date = form.start_time.data
        exam.start_time = form.start_time.data
        exam.end_time = form.end_time.data
        exam.duration = form.duration.data
        exam.is_private = form.is_private.data
        db.session.commit()
        flash('Exam updated successfully!', 'success')
        return redirect(url_for('manage_exam', exam_id=exam.id))
    elif request.method == 'GET':
        form.name.data = exam.name
        form.num_questions.data = exam.num_questions
        form.num_options.data = exam.num_options
        form.num_students.data = exam.num_students
        form.start_time.data = exam.start_time
        form.end_time.data = exam.end_time
        form.duration.data = exam.duration
        form.is_private.data = exam.is_private
    return render_template('create_exam.html', form=form, title='Edit Exam', is_edit=True)

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
        return redirect(url_for('dashboard'))
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
    now = datetime.utcnow()
    
    # Check if within window
    if exam.start_time and now < exam.start_time:
        flash(f'This exam is not yet available. It starts at {exam.start_time.strftime("%H:%M")}.', 'info')
        return redirect(url_for('dashboard'))
    if exam.end_time and now > exam.end_time:
        flash('This exam session has already ended.', 'danger')
        return redirect(url_for('dashboard'))

    # Check for existing attempt
    taken_exam = TakenExam.query.filter_by(user_id=current_user.id, exam_id=exam_id).first()
    
    # If they already finished (implied by an entry existing and we'll add a 'completed' flag or just check answers)
    # Actually, the user wants "cannot take it again after he has submitted it".
    # I'll add a 'completed_at' or just use the existence of answers.
    if taken_exam:
        # Check if they have answers (already submitted)
        if Answer.query.filter_by(user_id=current_user.id, exam_id=exam_id).first():
            flash('You have already submitted this exam.', 'info')
            return redirect(url_for('view_results', exam_id=exam_id))
    else:
        # Create attempt record when they first visit
        taken_exam = TakenExam(user_id=current_user.id, exam_id=exam_id, taken_at=now)
        db.session.add(taken_exam)
        db.session.commit()

    # Calculate personal deadline: min(taken_at + duration, exam.end_time)
    personal_deadline = taken_exam.taken_at + timedelta(minutes=exam.duration)
    if exam.end_time and personal_deadline > exam.end_time:
        personal_deadline = exam.end_time
        
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
    
    return render_template('take_exam.html', 
                           exam=exam, 
                           questions=questions, 
                           deadline=personal_deadline.isoformat())

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
    
    # Record TakenExam entry
    taken_exam = TakenExam(user_id=current_user.id, exam_id=exam_id)
    db.session.add(taken_exam)
    db.session.commit()
    
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    flash(f'Exam submitted successfully. Your score: {score:.2f}%', 'success')
    return redirect(url_for('dashboard'))

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
    return render_template('org_admin_dashboard.html', title='Organization Dashboard', organization=current_user.organization)

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

