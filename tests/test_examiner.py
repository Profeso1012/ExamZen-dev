import pytest
from examzen.models import User, Exam, Question, Organization

def test_examiner_dashboard_access(test_client):
    """
    GIVEN a logged-in Examiner
    WHEN accessing /dashboard
    THEN show the Examiner Dashboard
    """
    # Create and login examiner
    test_client.post('/register', data=dict(
        registration_type='individual',
        username='examiner1',
        email='examiner1@test.com',
        age=30,
        status='Examiner',
        password='password',
        confirm_password='password'
    ), follow_redirects=True)
    
    test_client.post('/login', data=dict(
        email='examiner1@test.com',
        password='password'
    ), follow_redirects=True)

    response = test_client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b"Examiner Dashboard" in response.data or b"Dashboard" in response.data
    assert b"Create New Exam" in response.data

def test_create_exam_flow(test_client):
    """
    GIVEN a logged-in Examiner
    WHEN submitting the Create Exam form
    THEN a new exam should be created in the DB
    """
    # Reuse login from previous or re-login if fixtures cleared DB
    test_client.post('/register', data=dict(
        registration_type='individual',
        username='examiner2',
        email='examiner2@test.com',
        age=30,
        status='Examiner',
        password='password',
        confirm_password='password'
    ), follow_redirects=True)
    
    test_client.post('/login', data=dict(
        email='examiner2@test.com',
        password='password'
    ), follow_redirects=True)

    # Convert datetime-local format 'YYYY-MM-DDTHH:MM'
    response = test_client.post('/create_exam', data=dict(
        name='Math 101 Final',
        num_questions=10,
        num_options=4,
        num_students=50,
        start_time='2025-06-01T09:00',
        end_time='2025-06-01T12:00',
        duration=60,
        is_private='y'
    ), follow_redirects=True)

    assert response.status_code == 200
    
    # Check DB
    exam = Exam.query.filter_by(name='Math 101 Final').first()
    assert exam is not None
    assert exam.duration == 60
    assert exam.is_private == True

def test_my_exams_list(test_client):
    """
    GIVEN a logged-in Examiner with exams
    WHEN accessing /my-exams
    THEN show the list of exams
    """
    # Create examiner and exam
    test_client.post('/register', data=dict(
        registration_type='individual',
        username='examiner3',
        email='examiner3@test.com',
        age=35,
        status='Examiner',
        password='password',
        confirm_password='password'
    ), follow_redirects=True)
    
    test_client.post('/login', data=dict(
        email='examiner3@test.com',
        password='password'
    ), follow_redirects=True)
    
    # Create Exam
    test_client.post('/create_exam', data=dict(
        name='History Quiz',
        num_questions=5,
        num_options=4,
        num_students=20,
        start_time='2025-07-01T10:00',
        end_time='2025-07-01T11:00',
        duration=30
    ), follow_redirects=True)
    
    response = test_client.get('/my-exams')
    assert response.status_code == 200
    assert b"History Quiz" in response.data

def test_manage_exam_access(test_client):
    """
    GIVEN a logged-in Examiner
    WHEN accessing manage page for their exam
    THEN show exam details
    """
    # reuse examiner3 from DB (in-memory per session usually, but fixtures might reset. Safe to recreate flow or assume per-test isolation if coded that way. content/conftest uses 'yield client', db.create_all per session vs per function? 
    # Current conftest uses 'yield client' inside 'with app.app_context()', DB is created/dropped per test function if scope='function' (default).
    
    test_client.post('/register', data=dict(
        registration_type='individual',
        username='examiner4',
        email='examiner4@test.com',
        age=35,
        status='Examiner',
        password='password',
        confirm_password='password'
    ), follow_redirects=True)
    
    test_client.post('/login', data=dict(
        email='examiner4@test.com',
        password='password'
    ), follow_redirects=True)
    
    test_client.post('/create_exam', data=dict(
        name='Biology Midterm',
        num_questions=50,
        num_options=4,
        num_students=100,
        start_time='2025-08-01T09:00',
        end_time='2025-08-01T12:00',
        duration=90
    ), follow_redirects=True)
    
    exam = Exam.query.filter_by(name='Biology Midterm').first()
    
    response = test_client.get(f'/exam/{exam.id}/manage')
    assert response.status_code == 200
    assert b"Biology Midterm" in response.data
    assert b"questions added" in response.data.lower()
