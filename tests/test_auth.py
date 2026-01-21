from examzen.models import User, Organization
from examzen import db

def test_home_page(test_client):
    """
    GIVEN a Flask application
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    response = test_client.get('/')
    assert response.status_code == 200
    assert b"ExamZen" in response.data

def test_register_individual(test_client):
    """
    GIVEN a Flask application
    WHEN the '/register' page is posted to with valid individual data
    THEN check that a new user is created
    """
    response = test_client.post('/register', data=dict(
        registration_type='individual',
        username='newstudent',
        email='student@test.com',
        age=21,
        status='Student',
        password='password',
        confirm_password='password'
    ), follow_redirects=True)
    
    assert response.status_code == 200
    # Check database
    user = User.query.filter_by(username='newstudent').first()
    assert user is not None
    assert user.email == 'student@test.com'
    assert user.status == 'Student'

def test_register_organization(test_client):
    """
    GIVEN a Flask application
    WHEN the '/register' page is posted to with valid organization data
    THEN check that a new organization and admin user are created
    """
    response = test_client.post('/register', data=dict(
        registration_type='organization',
        organization_name='TestOrg',
        email='org@test.com',
        password='password',
        confirm_password='password'
    ), follow_redirects=True)
    
    assert response.status_code == 200
    
    # Check Organization
    org = Organization.query.filter_by(name='TestOrg').first()
    assert org is not None
    
    # Check Admin User
    user = User.query.filter_by(email='org@test.com').first()
    assert user is not None
    assert user.organization_id == org.id
    assert user.status == 'Organization'
    # Check that username was set to org name as per our logic
    assert user.username == 'TestOrg'

def test_forgot_password_page(test_client):
    """
    GIVEN a Flask application
    WHEN the '/forgot_password' page is requested
    THEN check that the page loads
    """
    response = test_client.get('/forgot_password')
    assert response.status_code == 200
    assert b"Forgot Password" in response.data

def test_login_logout(test_client):
    """
    GIVEN a registered user
    WHEN login and logout actions occur
    THEN check session state
    """
    # Create a user first
    test_client.post('/register', data=dict(
        registration_type='individual',
        username='loginuser',
        email='login@test.com',
        age=25,
        status='Examiner',
        password='password',
        confirm_password='password'
    ), follow_redirects=True)

    # Login
    response = test_client.post('/login', data=dict(
        email='login@test.com',
        password='password'
    ), follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged in" in response.data
    
    # Logout
    response = test_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"Log in" in response.data # Check for 'Log in' link in navbar
