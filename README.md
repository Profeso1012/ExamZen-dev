# ExamZen

**ExamZen** is an online examination platform designed to help schools, organizations, and individuals create and manage online exams in real-time. It is especially useful during emergencies like pandemics when physical exams may not be possible.

### 📝 [Visit the live app here](https://exam-zen-dep-profeso1012-oluwaseyi-emmanuels-projects.vercel.app/register?_vercel_share=RakVlmWn3EVTIiWO6QO0Tnr8OZF0qzG3)

---

## Features

- **User Accounts**: Users can register, log in, and update their profiles.
- **Exams**: Create, manage, and take exams online.
- **Real-time Monitoring**: Admins can monitor exams as they happen.
- **Anti-cheating Measures**: Track and flag suspicious activity during exams.
- **Customizable Exams**: Set time limits, question types, and exam categories.

---

## Installation

To set up the project locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/examzen.git
   ```

2. Navigate to the project directory:
   ```bash
   cd examzen
   ```

3. Set up a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Set up environment variables in `.env` file:
   ```bash
   SECRET_KEY=your-secret-key
   SQLALCHEMY_DATABASE_URI=your-postgresql-uri
   ```

6. Run the app locally:
   ```bash
   flask run
   ```

---

## Technologies Used

- **Flask**: Python web framework.
- **SQLAlchemy**: ORM for database management.
- **PostgreSQL**: Database for storing data.
- **Vercel**: Hosting and deployment platform.
- **Docker**: For containerization (optional).

---

## Deployment

This app is deployed on [Vercel](https://vercel.com). Follow these steps to deploy your version:

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Link your project:
   ```bash
   vercel
   ```

3. Deploy:
   ```bash
   vercel deploy --prod
   ```

---

## Usage

You can use the app by visiting the following link: [ExamZen Live App](https://exam-zen-dep-profeso1012-oluwaseyi-emmanuels-projects.vercel.app/register?_vercel_share=RakVlmWn3EVTIiWO6QO0Tnr8OZF0qzG3).

1. Register a new account.
2. Log in using your credentials.
3. Explore the dashboard and create or take exams.
4. Admins can manage users and monitor exams.

---

## Contributing

If you wish to contribute to ExamZen, please fork the repository, create a new branch for your changes, and submit a pull request. Your contributions are welcome!

---
