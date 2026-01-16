from examzen import app, db
from examzen.models import User, Organization, Class, Exam, Question, Examoption, Answer, TakenExam, ProctorSession, Notification

def reset_db():
    print("Resetting database...")
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # specific triggers/initial data
        print("Database has been reset and all tables recreated.")

if __name__ == "__main__":
    reset_db()
