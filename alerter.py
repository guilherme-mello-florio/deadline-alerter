# alerter.py

import os
import smtplib
from email.mime.text import MIMEText
from datetime import date, timedelta

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, joinedload
from dotenv import load_dotenv

# Import your models by copying models.py into the same directory
from models import ProjectScheduleTask, User, Project

# --- CONFIGURATION ---
load_dotenv()

# Database Connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Email Configuration
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")


# --- EMAIL FUNCTION ---
def send_email(recipient_email: str, subject: str, body: str):
    """Sends a single email using SMTP."""
    if not all([MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM]):
        print("ERROR: Mail server credentials are not fully configured. Cannot send email.")
        return

    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = MAIL_FROM
    msg['To'] = recipient_email

    try:
        print(f"Connecting to mail server {MAIL_SERVER}:{MAIL_PORT}...")
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
            print(f"Successfully sent email to {recipient_email} with subject: '{subject}'")
    except Exception as e:
        print(f"ERROR: Failed to send email to {recipient_email}. Reason: {e}")


# --- MAIN LOGIC ---
def check_deadlines_and_send_alerts():
    """
    Queries for tasks with upcoming deadlines and sends alerts to all responsible users.
    """
    db = SessionLocal()
    try:
        today = date.today()
        one_day_away = today + timedelta(days=1)
        two_days_away = today + timedelta(days=2)

        print(f"Checking for deadlines on: {today}, {one_day_away}, and {two_days_away}")

        # --- MODIFIED: The query now joins on the 'responsible_users' relationship ---
        tasks_to_alert = db.query(ProjectScheduleTask).options(
            joinedload(ProjectScheduleTask.responsible_users),
            joinedload(ProjectScheduleTask.project)
        ).filter(
            ProjectScheduleTask.end_date.in_([today, one_day_away, two_days_away]),
            ProjectScheduleTask.status != 'Concluído'
        ).all()

        if not tasks_to_alert:
            print("No upcoming deadlines found. All good!")
            return

        print(f"Found {len(tasks_to_alert)} tasks with upcoming deadlines.")

        # --- MODIFIED: Loop through tasks, then through each responsible user ---
        for task in tasks_to_alert:
            project = task.project
            
            # If a task has no one assigned, skip it.
            if not task.responsible_users:
                print(f"WARNING: Task '{task.task_name}' (ID: {task.id}) has no responsible users assigned. Skipping alert.")
                continue

            # Loop through each assigned user and send them a personalized email.
            for user in task.responsible_users:
                # Determine the alert type
                days_until_due = (task.end_date - today).days
                if days_until_due == 0:
                    alert_type = "DUE TODAY"
                elif days_until_due == 1:
                    alert_type = "Due Tomorrow"
                else: # days_until_due == 2
                    alert_type = "Due in 2 Days"

                subject = f"Deadline Reminder [{alert_type}]: Task '{task.task_name}'"
                body = f"""
                <html>
                <body>
                    <p>Hi {user.username},</p>
                    <p>This is a friendly reminder about an upcoming deadline for a task you are responsible for:</p>
                    <ul>
                        <li><strong>Project:</strong> {project.project_name}</li>
                        <li><strong>Task:</strong> {task.task_name}</li>
                        <li><strong>Interface:</strong> {task.interface_name.replace('_', ' ')}</li>
                        <li><strong>Due Date:</strong> {task.end_date.strftime('%A, %B %d, %Y')} ({alert_type})</li>
                    </ul>
                    <p>Please ensure it is completed on time.</p>
                    <p>Thanks,<br>Wysupp Validate System</p>
                </body>
                </html>
                """
                
                if user.email:
                    send_email(user.email, subject, body)
                else:
                    print(f"WARNING: User '{user.username}' has no email address. Cannot send alert for task ID {task.id}.")

    finally:
        db.close()


if __name__ == "__main__":
    print("--- Starting Deadline Alerter Job ---")
    check_deadlines_and_send_alerts()
    print("--- Deadline Alerter Job Finished ---")
