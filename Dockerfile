# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Set environment variables (if needed)
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV SQLALCHEMY_DATABASE_URI=postgresql://default:Boiyph53JmOC@ep-winter-bonus-a45f5ljj-pooler.us-east-1.aws.neon.tech:5432/verceldb?sslmode=require
ENV SECRET_KEY=5791628bb0b13ce0c676dfde280ba245

# Expose port 5000 to the outside world
EXPOSE 5000

# Run Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
