from waitress import serve
from run import app  # Import your Flask app

serve(app, host='0.0.0.0', port=8000)
