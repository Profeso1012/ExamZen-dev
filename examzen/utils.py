import pandas as pd
from examzen import db
from examzen.models import Notification, User

def parse_questions_excel(file_stream):
    """
    Parses an uploaded Excel file for questions.
    Expected columns: 'Question Text', 'Option A', 'Option B', 'Option C', 'Option D', 
                      'Option E' (optional), 'Correct Answer', 'Marks' (optional)
    """
    try:
        df = pd.read_excel(file_stream)
        # Normalize headers
        df.columns = [c.strip().lower() for c in df.columns]
        
        questions = []
        for index, row in df.iterrows():
            # Basic validation - support both 'question' and 'question text'
            question_text = row.get('question text') or row.get('question')
            if pd.isna(question_text): 
                continue
            
            # Support both 'correct answer' and 'correct option'
            correct_answer = row.get('correct answer') or row.get('correct option')
            correct_letter = str(correct_answer).strip().upper() if not pd.isna(correct_answer) else None
            
            # Get marks if available
            marks = row.get('marks', 1)
            if pd.isna(marks):
                marks = 1
            
            q_data = {
                'text': str(question_text),
                'options': [],
                'correct': correct_letter,
                'marks': int(marks)
            }
            
            # Options A-E (support up to 5 options)
            letters = ['a', 'b', 'c', 'd', 'e']
            for i, letter in enumerate(letters):
                col_name = f'option {letter}'
                opt_text = row.get(col_name)
                if not pd.isna(opt_text):
                    q_data['options'].append({
                        'text': str(opt_text),
                        'letter': letter.upper(),
                        'is_correct': (letter.upper() == q_data['correct'])
                    })
            
            questions.append(q_data)
        return questions
    except Exception as e:
        print(f"Error parsing questions excel: {e}")
        return []

def parse_students_excel(file_stream):
    """
    Parses an uploaded Excel file for student emails.
    Expected columns: 'Email'
    """
    try:
        df = pd.read_excel(file_stream)
        df.columns = [c.strip().lower() for c in df.columns]
        
        if 'email' not in df.columns:
            return []
            
        return df['email'].dropna().tolist()
    except Exception as e:
        print(f"Error parsing students excel: {e}")
        return []

def send_notification(receiver_id, message, sender_id=None, type='general'):
    """
    Creates a notification for a user.
    """
    notif = Notification(
        receiver_id=receiver_id,
        sender_id=sender_id,
        message=message,
        type=type
    )
    db.session.add(notif)
    # Commit should usually be handled by the caller, but for utility we can flush
    db.session.flush() 
