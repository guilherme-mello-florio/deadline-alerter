# alerter.py

import os
import smtplib
from email.mime.text import MIMEText
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from dotenv import load_dotenv

# MODIFIED: Import ProjectInterfaceStatus as well
from models import ProjectScheduleTask, User, Project, ProjectInterfaceStatus

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
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
            print(f"Successfully sent email to {recipient_email} with subject: '{subject}'")
    except Exception as e:
        print(f"ERROR: Failed to send email to {recipient_email}. Reason: {e}")


# --- MAIN LOGIC ---
def check_deadlines_and_send_alerts():
    """
    Queries for tasks with upcoming deadlines, groups them by user, 
    and sends one summary alert email to each user with interface status.
    """
    db = SessionLocal()
    try:
        today = date.today()
        one_day_away = today + timedelta(days=1)
        two_days_away = today + timedelta(days=2)

        print(f"Checking for deadlines on: {today}, {one_day_away}, and {two_days_away}")

        # --- MODIFICATION 1: Fetch all interface statuses upfront for efficiency ---
        all_statuses = db.query(ProjectInterfaceStatus).all()
        status_map = {
            (status.project_id, status.interface_name): status.status
            for status in all_statuses
        }
        print(f"Loaded {len(status_map)} interface statuses.")

        # Query for all tasks with upcoming deadlines
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

        # Group tasks by responsible user
        tasks_by_user = {}
        for task in tasks_to_alert:
            for user in task.responsible_users:
                if user.id not in tasks_by_user:
                    tasks_by_user[user.id] = {'user_obj': user, 'tasks': []}
                tasks_by_user[user.id]['tasks'].append(task)

        # Loop through users and send one summary email each
        for user_id, data in tasks_by_user.items():
            user = data['user_obj']
            tasks = data['tasks']
            
            if not user.email:
                print(f"WARNING: User '{user.username}' has no email address. Cannot send alert.")
                continue

            # Build the list of tasks for the email body
            task_list_html = ""
            for task in sorted(tasks, key=lambda t: t.end_date):
                days_until_due = (task.end_date - today).days
                if days_until_due == 0:
                    alert_type = "DUE TODAY"
                elif days_until_due == 1:
                    alert_type = "Due Tomorrow"
                else:
                    alert_type = "Due in 2 Days"

                # --- MODIFICATION 2: Look up the status and add it to the email ---
                status_key = (task.project_id, task.interface_name)
                interface_status = status_map.get(status_key, "Status Unknown")

                task_list_html += f"""
                <li style="margin-bottom: 15px; padding: 10px; border-left: 4px solid #f59e0b; background-color: #fef9c3;">
                    <strong>Project:</strong> {task.project.project_name}<br>
                    <strong>Interface:</strong> {task.interface_name.replace('_', ' ')} (Status: {interface_status})<br>
                    <strong>Task:</strong> {task.task_name}<br>
                    <strong>Due Date:</strong> {task.end_date.strftime('%A, %B %d, %Y')} <strong style="color: #b45309;">({alert_type})</strong>
                </li>
                """

            subject = f"Deadline Reminder: You have {len(tasks)} tasks approaching their due dates"
            body = f"""
            <html>
            <body style="font-family: sans-serif;">
                <p>Hi {user.username},</p>
                <p>This is a friendly reminder about the following tasks you are responsible for that are approaching their deadlines:</p>
                <ul style="list-style: none; padding: 0;">
                    {task_list_html}
                </ul>
                <p>Please ensure they are completed on time.</p>
                <p>Thanks,<br>Wysupp Validate System</p>
            </body>
            </html>
            """
            
            send_email(user.email, subject, body)

    finally:
        db.close()


if __name__ == "__main__":
    print("--- Starting Deadline Alerter Job ---")
    check_deadlines_and_send_alerts()
    print("--- Deadline Alerter Job Finished ---")
