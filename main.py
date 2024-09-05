from kivy.uix.scrollview import ScrollView
from kivymd.uix.carousel import MDCarousel
from kivy.metrics import dp
from kivymd.uix.selectioncontrol import MDCheckbox, MDSwitch
from kivymd.uix.list import OneLineListItem
from kivymd.uix.card import MDCard
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton, MDFillRoundFlatIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.menu import MDDropdownMenu  # Use MDMenu for newer versions
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.navigationdrawer import MDNavigationDrawer, MDNavigationLayout
from kivy.uix.image import Image
from kivy.clock import Clock
import os
import imghdr
import uuid

from sqlalchemy import create_engine, Column, Integer, String, Enum, BLOB
from sqlalchemy import DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from functools import partial

Window.size = (350, 600)

# Database setup
engine = create_engine('mysql+mysqlconnector://fruit:fruit_pwd@localhost/examzen_db', echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()


# Define the User model
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    status = Column(Enum('Student', 'Examiner'), nullable=False)
    password = Column(String(255), nullable=False)
    profile_picture = Column(BLOB)

    answers = relationship("Answer", back_populates="user")


class Exam(Base):
    __tablename__ = 'exams'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    num_questions = Column(Integer, nullable=False)
    num_options = Column(Integer, nullable=False)
    num_students = Column(Integer, nullable=False)
    exam_date = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)  # in minutes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))

    questions = relationship("Question", back_populates="exam")
    exam_codes = relationship("ExamCode", back_populates="exam")
    answers = relationship("Answer", back_populates="exam")


class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey('exams.id'))
    question_text = Column(String(500), nullable=False)
    question_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    exam = relationship("Exam", back_populates="questions")
    options = relationship("Option", back_populates="question")
    answers = relationship("Answer", back_populates="question")


class Option(Base):
    __tablename__ = 'options'
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey('questions.id'))
    option_text = Column(String(200), nullable=False)
    option_letter = Column(String(1), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    question = relationship("Question", back_populates="options")


class ExamCode(Base):
    __tablename__ = 'exam_codes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey('exams.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    code = Column(String(10), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    exam = relationship("Exam", back_populates="exam_codes")
    user = relationship("User")


class Answer(Base):
    __tablename__ = 'answers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey('exams.id'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    answer = Column(String(200), nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    exam = relationship("Exam", back_populates="answers")
    question = relationship("Question", back_populates="answers")
    user = relationship("User", back_populates="answers")


# Create tables
Base.metadata.create_all(engine)

KV = """
ScreenManager:
    SplashScreen:
    LoginScreen:
    SignupScreen:
    UploadScreen:
    ExaminerDashboard:
    StudentDashboard:
    CreateExamScreen:
    ExamListScreen:
    ExamListScreenStudents:
    ExamReviewScreen:
    ExamViewScreen:
    TakeExamScreen:

<SplashScreen>:
    name: "splash"
    Image:
        source: 'zen-icon.png'
        size_hint: (1, 1)
        allow_stretch: True

<LoginScreen>:
    name: "login"
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)

        MDTextField:
            id: username_field
            hint_text: "Enter your username"
        MDTextField:
            id: password_field
            hint_text: "Enter your password"
            password: True
        MDRaisedButton:
            text: "Login"
            on_release: app.login(username_field.text, password_field.text)
        MDRaisedButton:
            text: "Sign Up"
            on_release: app.switch_to_signup()

<SignupScreen>:
    name: "signup"
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)
        MDTextField:
            id: new_username_field
            hint_text: "Enter your username"
        MDTextField:
            id: email_field
            hint_text: "Enter your email"
        MDTextField:
            id: age_field
            hint_text: "Enter your age"
            input_filter: 'int'
        MDTextField:
            id: status_field
            hint_text: "Select Status"
            readonly: True
            on_focus: if self.focus: app.show_status_menu(self)
        MDTextField:
            id: password1_field
            hint_text: "Enter your password"
            password: True
        MDTextField:
            id: password2_field
            hint_text: "Confirm your password"
            password: True
        MDRaisedButton:
            text: "Submit"
            on_release: app.validate_signup()

<UploadScreen>:
    name: "upload"
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)

        MDRaisedButton:
            text: "Choose Avatar"
            on_release: app.file_manager_open()

        MDRaisedButton:
            text: "Done"
            on_release: app.status_profile()


<ExaminerDashboard>:
    name: 'examiner_dashboard'
    MDNavigationLayout:
        ScreenManager:
            Screen:
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(20)
                    spacing: dp(20)
                    MDTopAppBar:
                        title: "Profile"
                        left_action_items: [['menu', lambda x: nav_drawer1.set_state("toggle")]]
                        right_action_items: [["dots-vertical", lambda x: app.nulll(x)], ["clock", lambda x: app.nulll(x)]]
                        elevation: 10
                    MDLabel:
                        text: 'Examiner Dashboard'
                        halign: 'center'
                        font_style: 'H5'
                    MDRaisedButton:
                        text: 'Create Exam'
                        on_release: root.manager.current = 'create_exam'
                    MDRaisedButton:
                        text: 'Update Exam'
                        on_release: app.show_exam_list()
                    MDRaisedButton:
                        text: 'Monitor Results'
                        on_release: app.monitor_results()
                    MDRaisedButton:
                        text: 'Logout'
                        on_release: app.logout1()
                    Widget:

        ProfileNavD:
            id: nav_drawer1
            size_hint: (0.95, 0.9)

<StudentDashboard>:
    name: 'student_dashboard'
    MDNavigationLayout:
        ScreenManager:
            Screen:
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(20)
                    spacing: dp(20)
                    MDTopAppBar:
                        title: "Profile"
                        left_action_items: [['menu', lambda x: nav_drawer2.set_state("toggle")]]
                        right_action_items: [["dots-vertical", lambda x: app.nulll(x)], ["clock", lambda x: app.nulll(x)]]
                        elevation: 10
                    MDLabel:
                        text: 'Student Dashboard'
                        halign: 'center'
                        font_style: 'H5'
                    MDRaisedButton:
                        text: 'Available Exams'
                        on_release: app.list_available_exams()
                    MDRaisedButton:
                        text: 'View Results'
                        on_release: app.view_results()
                    MDRaisedButton:
                        text: 'Send Complaint'
                        on_release: app.send_complaint()
                    MDRaisedButton:
                        text: 'Logout'
                        on_release: app.logout1()
                    Widget:

        ProfileNavD:
            id: nav_drawer2
            size_hint: (0.95, 0.9)


<CreateExamScreen>:
    name: 'create_exam'
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)

        ScrollView:
            size_hint_y: None
            height: dp(400)  # adjust the height as needed

            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height

                MDTextField:
                    id: exam_name
                    hint_text: "Exam Name"

                MDTextField:
                    id: num_questions
                    hint_text: "Number of Questions (max 10)"
                    input_filter: 'int'

                MDTextField:
                    id: num_options
                    hint_text: "Number of Options per Question"
                    input_filter: 'int'

                MDTextField:
                    id: num_students
                    hint_text: "Number of Students (max 15)"
                    input_filter: 'int'

                MDTextField:
                    id: exam_date
                    hint_text: "Exam Date (YYYY-MM-DD)"

                MDTextField:
                    id: exam_time
                    hint_text: "Exam Time (HH:MM)"

                MDTextField:
                    id: duration
                    hint_text: "Duration (minutes, max 30)"
                    input_filter: 'int'

        BoxLayout:
            orientation: 'horizontal'
            padding: dp(20)
            spacing: dp(20)

            MDRaisedButton:
                text: "Create"
                on_release: app.create_exam()

            MDRaisedButton:
                text: "Back"
                on_release:
                    app.root.transition.direction = 'left'
                    app.root.current = 'examiner_dashboard'

<ExamListScreen>:
    name: 'exam_list'
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)
        MDLabel:
            text: 'Your Exams'
            halign: 'center'
            font_style: 'H5'
        ScrollView:
            MDList:
                id: exam_list
        BoxLayout:
            orientation: 'horizontal'
            padding: dp(20)
            spacing: dp(20)
            MDRaisedButton:
                text: "Back"
                on_release:
                    app.root.transition.direction = 'left'
                    app.root.current = 'examiner_dashboard'

<ExamListScreenStudents>:
    name: 'exam_list_students'
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)
        MDLabel:
            text: 'Available Exams'
            halign: 'center'
            font_style: 'H5'
        ScrollView:
            MDList:
                id: exam_list_view
        BoxLayout:
            orientation: 'horizontal'
            padding: dp(20)
            spacing: dp(20)
            MDRaisedButton:
                text: "Back"
                on_release:
                    app.root.transition.direction = 'left'
                    app.root.current = 'student_dashboard'                  

<ExamReviewScreen>:
    name: 'exam_review'
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)

        MDLabel:
            id: exam_name
            halign: 'center'
            font_style: 'H5'
            size_hint_y: None
            height: dp(50)

        BoxLayout:
            orientation: 'vertical'
            size_hint_y: 0.9
            ScrollView:
                Carousel:
                    id: question_carousel
                    size_hint_y: None
                    height: dp(200)

        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: dp(50)
            padding: dp(10)
            spacing: dp(10)

            MDIconButton:
                icon: "chevron-left"
                on_release: app.carousel_previous()

            MDRaisedButton:
                text: "Save Changes"
                on_release: app.save_exam_changes()

            MDIconButton:
                icon: "chevron-right"
                on_release: app.carousel_next()

        MDRaisedButton:
            text: "Back to Exam List"
            on_release:
                app.root.transition.direction = 'left'
                app.root.current = 'exam_list'


<ProfileNavD>:
    size_hint: (0.95, 0.9)
    BoxLayout:
        orientation: 'vertical'
        padding: '8dp'
        spacing: '8dp'

        Image:
            id: avatar
            size_hint: (1, 1)
            source: app.user_profile_picture
        MDLabel:
            id: username_label
            text: f"       {app.user_name}"
            font_style: "Subtitle1"
            size_hint_y: None
            height: self.texture_size[1]
        MDLabel:
            id: email_label
            text: f"       {app.user_email}"
            size_hint_y: None
            font_style: "Caption"
            height: self.texture_size[1]
        ScrollView:
            MDList:
                id: md_list  
                OneLineIconListItem:
                    text: "Profile"                            
                    IconLeftWidget:
                        icon: "face-profile"                                                                        
                OneLineIconListItem:
                    text: "Upload"                           
                    IconLeftWidget:
                        icon: "upload"                                                          
                OneLineIconListItem:
                    text: "Logout"                            
                    on_release: app.logout1()
                    IconLeftWidget:
                        icon: "logout"
   


<ExamViewScreen>:
    name: 'exam_view'
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(20)
        MDLabel:
            text: 'Exam Details'
            halign: 'center'
            font_style: 'H5'
        Carousel:
            id: exam_carousel
            # You can add additional widgets here to display exam details
        BoxLayout:
            orientation: 'horizontal'
            padding: dp(20)
            spacing: dp(20)
            MDRaisedButton:
                text: "Back"
                on_release:
                    app.root.transition.direction = 'left'
                    app.root.current = 'exam_list_students'

<TakeExamScreen>:
    name: "take_exam"
    BoxLayout:
        orientation: 'vertical'
        MDLabel:
            text: 'An Exam'
            halign: 'center'
            text_color: (0,1,0,1)
            font_style: 'H5'
            size_hint_y: None
            height: dp(50)
        MDCarousel:
            id: question_carousel
            size_hint: (1, 0.8)
            # Question screens will be added dynamically here

        BoxLayout:
            id: finish_button_box
            size_hint_y: None
            height: '48dp'

"""


class SplashScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.switch_to_login, 7)

    def switch_to_login(self, dt):
        self.manager.current = 'login'


class LoginScreen(Screen):
    pass


class SignupScreen(Screen):
    pass


class UploadScreen(Screen):
    pass


class UpdateScreen(Screen):
    pass


class ExaminerDashboard(Screen):
    pass


class StudentDashboard(Screen):
    pass


class CreateExamScreen(Screen):
    pass


class ExamListScreen(Screen):
    pass


class ExamListScreenStudents(Screen):
    pass


class ExamReviewScreen(Screen):
    pass


class ProfileNavD(MDNavigationDrawer):
    pass


class ExamViewScreen(Screen):
    pass

    #-----------------------

class TakeExamScreen(Screen):
    pass


class DemoApp(MDApp):
    def build(self):
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager,
            select_path=self.select_path
        )
        self.selected_image_path = ""
        self.question_data = []
        self.user_email = "user@example.com"
        self.user_name = "username"
        self.user_profile_picture = "zen-icon.png"
        self.theme_cls.primary_palette = "Red"
        return Builder.load_string(KV)

    def on_start(self):
        self.current_exam = None
        self.current_question = 1

    def login(self, username, password):
        user = session.query(User).filter_by(username=username, password=password).first()
        if user:
            # Store user data for later use
            self.user_name = user.username
            self.user_id = user.id
            self.user_email = user.email
            self.user_age = user.age
            self.user_status = user.status
            self.user_profile_picture = user.profile_picture
            self.current_user = user

            if user.status == 'Examiner':
                self.root.current = 'examiner_dashboard'
            else:
                self.root.current = 'student_dashboard'
        else:
            self.show_error_dialog("Invalid username or password.")

    def status_profile(self):
        statt = self.user_status
        if statt == 'Examiner':
            self.root.current = 'examiner_dashboard'
        else:
            self.root.current = 'student_dashboard'

    def show_status_menu(self, instance):
        menu_items = [
            {"text": "Student", "on_release": lambda: self.set_status("Student")},
            {"text": "Examiner", "on_release": lambda: self.set_status("Examiner")},
        ]
        self.status_menu = MDDropdownMenu(
            caller=instance,
            items=menu_items,
            position="bottom",
            width_mult=4,
        )
        self.status_menu.open()

    def set_status(self, status):
        self.root.get_screen('signup').ids.status_field.text = status
        self.status_menu.dismiss()

    def validate_signup(self):
        signup_screen = self.root.get_screen('signup')
        username = signup_screen.ids.new_username_field.text
        email = signup_screen.ids.email_field.text
        age = signup_screen.ids.age_field.text
        status = signup_screen.ids.status_field.text
        password1 = signup_screen.ids.password1_field.text
        password2 = signup_screen.ids.password2_field.text

        # Check for existing username or email
        existing_user = session.query(User).filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            self.show_error_dialog("This username or email already exists. Please choose a different one.")
            return

        if not "@" in email:
            self.show_error_dialog("Invalid email address.")
        elif not age.isdigit() or int(age) < 2 or int(age) > 60:
            self.show_error_dialog("Age must be between 2 and 60.")
        elif not status:
            self.show_error_dialog("Please select a status.")
        elif password1 != password2:
            self.show_error_dialog("Passwords do not match.")
        else:
            # Insert data into SQLAlchemy ORM
            new_user = User(
                username=username,
                email=email,
                age=int(age),
                status=status,
                password=password1  # Ideally, you should hash the password here
            )
            session.add(new_user)
            session.commit()

            # Refresh the user object to get the assigned ID
            session.refresh(new_user)

            # Set user data for the current session
            self.user_name = new_user.username
            self.user_id = new_user.id
            self.user_email = new_user.email
            self.user_age = new_user.age
            self.user_status = new_user.status
            self.user_profile_picture = new_user.profile_picture if hasattr(new_user, 'profile_picture') else None
            self.current_user = new_user

            self.root.current = "upload"

        # user = session.query(User).filter_by(username=username).first()
        # self.user_id = user.id

    def switch_to_signup(self):
        self.root.current = "signup"

    def file_manager_open(self):
        self.file_manager.show(os.path.expanduser("~"))

    def select_path(self, path):
        self.selected_image_path = path
        with open(path, 'rb') as file:
            image_data = file.read()
        user = session.query(User).filter_by(username=self.user_name).first()
        if user:
            user.profile_picture = image_data
            session.commit()
        self.exit_manager()
        self.status_profile()

    def exit_manager(self, *args):
        self.file_manager.close()

    def toggle_nav_drawer(self):
        nav_drawer = self.root.ids.nav_drawer
        if nav_drawer.state == 'open':
            nav_drawer.set_state('close')
        else:
            nav_drawer.set_state('open')

    def go_to_profile_screen(self):
        nav_drawer = self.root.ids.nav_drawer
        nav_drawer.set_state('close')

    def go_to_upload_screen(self):
        self.root.current = "upload"

    def display_profile(self):
        profile_screen = self.root.get_screen('profile')

        profile_screen.ids.profile_name.text = f"Username: {self.user_name}"
        profile_screen.ids.profile_email.text = f"Email: {self.user_email}"
        profile_screen.ids.profile_age.text = f"Age: {self.user_age}"
        profile_screen.ids.profile_status.text = f"Status: {self.user_status}"

        if self.user_profile_picture:
            # Save the profile picture to a temporary file
            temp_file = 'temp_profile_pic.jpg'
            with open(temp_file, 'wb') as file:
                file.write(self.user_profile_picture)
            profile_screen.ids.avatar_image.source = temp_file
        else:
            profile_screen.ids.avatar_image.source = 'zen-icon.png'  # Make sure you have a default avatar image

        self.root.current = "profile"

    def show_error_dialog(self, message):
        self.dialog = MDDialog(
            text=message,
            buttons=[MDRaisedButton(text="OK", on_release=self.close_dialog)]
        )
        self.dialog.open()

    def close_dialog(self, *args):
        self.dialog.dismiss()

    def show_menu(self, instance):
        menu_items = [
            {"text": "Edit User Name", "viewclass": "OneLineListItem",
             "on_release": lambda: self.edit_username()},
            {"text": "Change DP", "viewclass": "OneLineListItem", "on_release": lambda: self.change_dp()},
            {"text": "Logout", "viewclass": "OneLineListItem", "on_release": lambda: self.logout()},
        ]
        self.menu = MDDropdownMenu(
            caller=instance,
            items=menu_items,
            width_mult=4,
        )
        self.menu.open()

    def nulll(self, instance):
        self.show_error_dialog("Not yet Implemented")

    def edit_profile(self):
        # Implement profile editing logic
        pass

    def edit_username(self):
        self.menu.dismiss()
        self.root.current = "update"
        update_screen = self.root.get_screen('update')
        update_screen.ids.update_username_field.text = self.user_name

    def change_dp(self):
        self.menu.dismiss()
        self.root.current = "upload"

    def update_profile(self):
        update_screen = self.root.get_screen('update')
        new_username = update_screen.ids.update_username_field.text

        # Check if the new username already exists
        existing_user = session.query(User).filter(User.username == new_username,
                                                   User.username != self.user_name).first()
        if existing_user:
            self.show_error_dialog("This username already exists. Please choose a different one.")
            return

        user = session.query(User).filter_by(username=self.user_name).first()
        if user:
            user.username = new_username
            session.commit()
            self.user_name = new_username
            self.show_error_dialog("Username updated successfully!")
            self.display_profile()
        else:
            self.show_error_dialog("Error updating username. Please try again.")
        # --------------------------------------------------------------#

    def create_exam(self):
        create_exam_screen = self.root.get_screen('create_exam')
        exam_name = create_exam_screen.ids.exam_name.text.strip()

        # Validate input fields
        required_fields = [
            ('num_questions', "Number of Questions"),
            ('num_options', "Number of Options"),
            ('num_students', "Number of Students"),
            ('duration', "Duration"),
        ]

        for field_id, field_name in required_fields:
            if not create_exam_screen.ids[field_id].text.strip():
                self.show_error_dialog(f"{field_name} is required.")
                return

        try:
            num_questions = int(create_exam_screen.ids.num_questions.text)
            num_options = int(create_exam_screen.ids.num_options.text)
            num_students = int(create_exam_screen.ids.num_students.text)
            duration = int(create_exam_screen.ids.duration.text)
        except ValueError:
            self.show_error_dialog("Please enter valid numbers for questions, options, students, and duration.")
            return

        exam_date = create_exam_screen.ids.exam_date.text
        exam_time = create_exam_screen.ids.exam_time.text

        # Validate input
        if not exam_name:
            self.show_error_dialog("Exam name is required.")
            return
        if num_questions > 10 or num_students > 15 or duration > 30:
            self.show_error_dialog("Invalid input. Please check your entries.")
            return

        # Validate date and time format
        try:
            exam_datetime = datetime.strptime(f"{exam_date} {exam_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            self.show_error_dialog("Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time.")
            return

        # Create exam in database
        new_exam = Exam(
            name=exam_name,
            num_questions=num_questions,
            num_options=num_options,
            num_students=num_students,
            exam_date=exam_datetime,
            duration=duration,
            created_by=self.user_id
        )
        session.add(new_exam)
        session.commit()

        # Generate exam codes for students
        for _ in range(num_students):
            code = self.generate_unique_exam_code()
            exam_code = ExamCode(exam_id=new_exam.id, code=code)
            session.add(exam_code)
        session.commit()

        # Reset question_data list for the new exam
        self.question_data = []

        # Move to question creation
        self.current_exam = new_exam
        self.current_question = 1
        self.setup_question_carousel()

    def generate_unique_exam_code(self):
        # Generate a unique 10-character code using UUID
        unique_id = str(uuid.uuid4())[:7].upper()
        return unique_id

    def setup_question_carousel(self):
        # Assuming self.current_exam.num_questions gives the number of questions
        carousel = self.root.get_screen('exam_review').ids.question_carousel
        carousel.clear_widgets()  # Clear any existing widgets

        # Loop to add questions as screens within the carousel
        for question_number in range(1, self.current_exam.num_questions + 1):
            screen = self.create_question_screen(question_number)  # Assuming this creates the content for each question
            carousel.add_widget(screen)

        self.root.current = 'exam_review'

    def carousel_previous(self):
        carousel = self.root.get_screen('exam_review').ids.question_carousel
        carousel.load_previous()

    def carousel_next(self):
        carousel = self.root.get_screen('exam_review').ids.question_carousel
        carousel.load_next()

    def create_question_screen(self, question_number):
        screen = Screen()
        scroll_view = ScrollView()
        main_box = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20), size_hint_y=None)
        main_box.bind(minimum_height=main_box.setter('height'))

        main_box.add_widget(MDLabel(text=f"Question {question_number}", halign="center", font_style="H5"))

        question_text = MDTextField(hint_text="Enter question text", multiline=True, size_hint_y=None, height=dp(100))
        main_box.add_widget(question_text)

        options_box = BoxLayout(orientation='vertical', spacing=dp(15), size_hint_y=None)
        options_box.bind(minimum_height=options_box.setter('height'))
        options = []
        for i in range(self.current_exam.num_options):
            option_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(48))
            option_text = MDTextField(hint_text=f"Option {chr(65 + i)}", size_hint_x=0.8)
            is_correct = MDCheckbox(size_hint=(None, None), size=(48, 48))

            option_layout.add_widget(option_text)
            option_layout.add_widget(is_correct)
            options_box.add_widget(option_layout)

            options.append({'text': option_text, 'correct': is_correct})

        main_box.add_widget(options_box)

        save_button = MDRaisedButton(text="Save & Next",
                                     on_release=lambda *args: self.save_question(question_number, question_text.text,
                                                                                 options),
                                     pos_hint={'center_x': 0.5})
        main_box.add_widget(save_button)

        scroll_view.add_widget(main_box)
        screen.add_widget(scroll_view)

        return screen


    def save_exam_changes(self):
        # Check if there are any questions saved
        if not self.root.get_screen('exam_review').ids.question_carousel.slides:
            self.show_error_dialog("No questions have been saved yet.")
            return

        # Show confirmation dialog if there are questions
        self.show_confirmation_dialog("Save Exam", self.confirm_save)

    def show_confirmation_dialog(self, message, confirm_action):
        self.dialog = MDDialog(
            title="Confirmation",
            text=message,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.dismiss_dialog),
                MDRaisedButton(text="CONFIRM", on_release=lambda *args: confirm_action(*args)),
            ],
        )
        self.dialog.open()

    def dismiss_dialog(self, *args):
        self.dialog.dismiss()

    def confirm_save(self, *args):
        self.dialog.dismiss()
        self.save_to_database()

    def save_to_database(self):
        try:
            for i, question in enumerate(self.question_data):
                existing_question = session.query(Question).filter_by(exam_id=self.current_exam.id,
                                                                      question_number=i + 1).first()
                if existing_question:
                    existing_question.question_text = question['question']
                    # Delete existing options for this question
                    session.query(Option).filter_by(question_id=existing_question.id).delete()
                else:
                    existing_question = Question(exam_id=self.current_exam.id, question_text=question['question'],
                                                 question_number=i + 1)
                    session.add(existing_question)
                    session.flush()  # This will populate the id of the new question

                # Add new options for this question
                for j, option in enumerate(question['options']):
                    new_option = Option(
                        question_id=existing_question.id,
                        option_text=option['text'],
                        is_correct=option['correct'],
                        option_letter=chr(65 + j)
                    )
                    session.add(new_option)

            session.commit()
            self.show_success_dialog("Exam saved successfully!")
            # Clear question data after successful save
            self.question_data.clear()

        except Exception as e:
            session.rollback()
            self.show_error_dialog(f"Error saving exam: {str(e)}")

    def show_success_dialog(self, message):
        self.dialog = MDDialog(
            title="Success",
            text=message,
            buttons=[MDFlatButton(text="OK", on_release=self.dismiss_dialog)],
        )
        self.dialog.open()

    def show_error_dialog(self, message):
        self.dialog = MDDialog(
            title="Error",
            text=message,
            buttons=[MDFlatButton(text="OK", on_release=self.dismiss_dialog)],
        )
        self.dialog.open()

    def save_question(self, question_number, question_text, options):
        question_data = {
            'question': question_text,
            'options': [{'text': option['text'].text, 'correct': option['correct'].active} for option in options]
        }

        if question_number <= len(self.question_data):
            self.question_data[question_number - 1] = question_data
        else:
            self.question_data.append(question_data)

        if question_number == self.current_exam.num_questions:
            # Pass a message and the action to take when the confirmation is positive
            self.show_confirmation_dialog("Save Exam", self.confirm_save)
        else:
            self.root.get_screen('exam_review').ids.question_carousel.load_next()

    def finish_exam(self):
        self.show_success_dialog("Your exam has been successfully created.")
        self.root.current = 'examiner_dashboard'

    def show_exam_list(self):
        exams = session.query(Exam).filter_by(created_by=self.current_user.id).all()
        exam_list = self.root.get_screen('exam_list').ids.exam_list
        exam_list.clear_widgets()
        for exam in exams:
            item = OneLineListItem(text=exam.name, on_release=lambda x, exam_id=exam.id: self.show_exam_review(exam_id))
            exam_list.add_widget(item)
        self.root.current = 'exam_list'

    def show_exam_review(self, exam_id):
        self.current_exam = session.query(Exam).get(exam_id)
        self.setup_question_carousel()

    def monitor_exam(self):
        # Implement exam monitoring logic
        pass

    def monitor_results(self):
        # Implement results monitoring logic
        pass

    # students-----------------------------------------start
    def list_available_exams(self):
        exams = session.query(Exam).all()
        exam_list_view = self.root.get_screen('exam_list_students').ids.exam_list_view
        exam_list_view.clear_widgets()

        for exam in exams:
            item = OneLineListItem(text=exam.name, on_release=lambda x, exam_id=exam.id: self.open_exam(exam_id))
            exam_list_view.add_widget(item)
        self.root.current = 'exam_list_students'

    def open_exam(self, exam_id):
        self.current_exam_id = exam_id
        exam = session.query(Exam).filter_by(id=exam_id).first()
        questions = session.query(Question).filter_by(exam_id=exam_id).all()
        exam_view_screen = self.root.get_screen('take_exam')
        carousel = exam_view_screen.ids.question_carousel
        carousel.clear_widgets()

        for index, question in enumerate(questions, start=1):
            question_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

            question_label = MDLabel(
                text=f"Question {index}: {question.question_text}",
                size_hint_y=None,
                height=dp(100),
                text_color=(0, 1, 0, 1)
            )
            question_layout.add_widget(question_label)

            options_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
            options_box.bind(minimum_height=options_box.setter('height'))
            self.create_option_checkboxes(options_box, question.options, question.id)

            scroll_view = ScrollView(size_hint=(1, None), height=dp(200))
            scroll_view.add_widget(options_box)
            question_layout.add_widget(scroll_view)

            save_button = MDRaisedButton(
                text="Save Answer",
                on_release=lambda x, q_id=question.id: self.save_answer(q_id),
                size_hint_y=None,
                height=dp(40)
            )
            question_layout.add_widget(save_button)

            carousel.add_widget(question_layout)

        # Add navigation buttons
        nav_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10),
                            pos_hint={"center_x": 0.5, "center_y": 0.25})
        prev_button = MDIconButton(icon="chevron-left", on_release=self.carousel_previous1)
        next_button = MDIconButton(icon="chevron-right", on_release=self.carousel_next1)
        nav_box.add_widget(prev_button)
        nav_box.add_widget(next_button)
        exam_view_screen.add_widget(nav_box)

        finish_button = MDRaisedButton(
            text="Finish Exam",
            on_release=self.finish_exam1,
            size_hint_y=None, height=dp(40)
        )
        exam_view_screen.ids.finish_button_box.clear_widgets()
        exam_view_screen.ids.finish_button_box.add_widget(finish_button)
        self.root.current = 'take_exam'

    def create_option_checkboxes(self, box, options, question_id):
        option_group = []
        for index, option in enumerate(options):
            checkbox = MDCheckbox(group=f'question_{question_id}', size_hint=(None, None), size=(48, 48))
            option_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48))
            option_layout.add_widget(checkbox)
            option_label = MDLabel(text=f"{chr(65 + index)}. {option.option_text}")
            option_layout.add_widget(option_label)
            box.add_widget(option_layout)
            option_group.append((checkbox, chr(65 + index)))  # Store checkbox and option letter
        setattr(self, f'question_{question_id}_options', option_group)

    def save_answer(self, question_id):
        print(f"save_answer called for question ID: {question_id}")  # Debug print
        option_group = getattr(self, f'question_{question_id}_options', [])
        selected_option = next((option_letter for checkbox, option_letter in option_group if checkbox.active), None)

        if selected_option:
            print(f"Selected option for question {question_id}: {selected_option}")  # Debug print
            existing_answer = session.query(Answer).filter_by(
                exam_id=self.current_exam_id,
                question_id=question_id,
                user_id=self.user_id
            ).first()

            if existing_answer:
                existing_answer.answer = selected_option
                print(f"Updated existing answer for question ID: {question_id}")  # Debug print
            else:
                new_answer = Answer(
                    exam_id=self.current_exam_id,
                    question_id=question_id,
                    user_id=self.user_id,
                    answer=selected_option,
                    is_correct=False  # This will be evaluated later
                )
                session.add(new_answer)
                print(f"Saved new answer for question ID: {question_id}")  # Debug print

            try:
                session.commit()
                self.show_success_dialog("Answer saved successfully!")
            except Exception as e:
                session.rollback()
                self.show_error_dialog(f"Error saving answer: {str(e)}")
        else:
            self.show_error_dialog("Please select an answer before saving.")

    def carousel_previous1(self, *args):
        carousel = self.root.get_screen('take_exam').ids.question_carousel
        carousel.load_previous()

    def carousel_next1(self, *args):
        carousel = self.root.get_screen('take_exam').ids.question_carousel
        carousel.load_next()

    def finish_exam1(self, *args):
        # Check if all questions have been answered
        questions = session.query(Question).filter_by(exam_id=self.current_exam_id).all()
        answers = session.query(Answer).filter_by(exam_id=self.current_exam_id, user_id=self.user_id).all()

        if len(answers) < len(questions):
            self.show_error_dialog("Please answer all questions before finishing the exam.")
            return

        self.show_confirmation_dialog("Are you sure you want to finish the exam?", self.confirm_finish_exam)

    def confirm_finish_exam(self, *args):
        self.dismiss_dialog()
        self.show_success_dialog("Exam finished successfully!")
        self.root.current = "student_dashboard"


    def save_all_answers(self):
        carousel = self.root.get_screen('take_exam').ids.question_carousel
        answer_data = []

        for screen in carousel.slides:
            question_id = int(screen.name.split("_")[1])
            selected_option = None

            for child in screen.children:
                if isinstance(child, BoxLayout):
                    for option in child.children:
                        if isinstance(option, BoxLayout):
                            for item in option.children:
                                if isinstance(item, MDCheckbox) and item.active:
                                    selected_option = item
                                    break
                            if selected_option:
                                break
                    if selected_option:
                        break

            if selected_option:
                answer_data.append((self.current_exam_id, question_id, self.get_current_user_id(), selected_option.text))

        for exam_id, question_id, user_id, answer_text in answer_data:
            new_answer = Answer(
                exam_id=exam_id,
                question_id=question_id,
                user_id=user_id,
                answer=answer_text,
                is_correct=False
            )
            session.add(new_answer)

        session.commit()
        self.show_success_dialog("All answers have been saved successfully!")

    # students----------------------------------------end
    def view_results(self):
        # Implement student results viewing logic
        pass

    def send_complaint(self):
        # Implement complaint sending logic
        pass

    def logout(self):
        self.menu.dismiss()
        self.show_error_dialog("Logging out...")
        # Implement logout logic here
        Clock.schedule_once(self.close_app, 4)

    # ------------------------------------------------------#
    def logout1(self):
        self.show_error_dialog("Logging out...")
        # Implement logout logic here
        Clock.schedule_once(self.close_app, 4)

    def close_app(self, *args):
        App.get_running_app().stop()


if __name__ == '__main__':
    DemoApp().run()

