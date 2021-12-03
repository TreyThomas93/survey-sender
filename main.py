"""
FETCH EVENTS FROM CALENDLY AND SEND SURVEY TO STUDENTS EMAIL 1 HOUR AFTER EVENT ENDS.
THIS WILL EXECUTE EVERY HOUR AND BOTH SAVE STUDENT DATA TO FILE AND SEND SURVEY EMAIL WITH STUDENT DATA IF WARRANTED.
"""
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

load_dotenv(dotenv_path="config.env")

API_TOKEN = os.getenv("API_TOKEN")
PASSWORD = os.getenv("PASSWORD")
SEND_SURVEY = True if os.getenv("SEND_SURVEY") == "True" else False


class SurveySender:

    def __init__(self):
        self.base_url = "https://api.calendly.com/"
        self.headers = {
            'Content-Type': "application/json",
            'Authorization': f"Bearer {API_TOKEN}"
        }

    def getSessions(self):
        url = f"{self.base_url}scheduled_events"
        payload = {
            "user": f"{self.base_url}users/3ab7508f-1a22-4b83-9373-683b8f4d771e",
            "min_start_time": datetime.utcnow(),
            "max_start_time": datetime.utcnow() + timedelta(hours=6),
            "status": "active"
        }

        return self.sendRequest(url, payload)

    def getStudents(self, sessions):
        # [{'email': 'treythomas93@gmail.com',
        #   'end_time': '2021-12-01T18:00:00.000000Z',
        #   'name': 'Trey Thomas',
        #   'start_time': '2021-12-01T17:00:00.000000Z',
        #   'time_to_send': '2021-12-01T19:00:00.000000Z',
        #   'uuid': '0b1ae5de-d696-4ddb-a9eb-a4ea116a9dd4'}]
        students = []
        for session in sessions["collection"]:
            obj = {
                "start_time": session["start_time"],
                "end_time": session["end_time"],
                "time_to_send": (datetime.strptime(session["end_time"], '%Y-%m-%dT%H:%M:%S.%fZ') + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }
            url = f"{session['uri']}/invitees"
            invitees = self.sendRequest(url)
            obj["name"] = invitees["collection"][0]["name"]
            obj["email"] = invitees["collection"][0]["email"]
            obj["uuid"] = invitees["collection"][0]["uri"].split(
                "/")[-1].strip()
            students.append(obj)

        return students

    def saveStudents(self, students):
        with open(f"{THIS_FOLDER}/students.json", "r") as f:
            data = json.load(f)
            saved_uuid = [i["uuid"] for i in data]
            students = [*data, *[student for student in students if student["uuid"] not in saved_uuid]]
        with open(f"{THIS_FOLDER}/students.json", "w") as f:
            f.write(json.dumps(students, indent=4))

    def sendRequest(self, url, payload=None):
        try:
            response = requests.get(url, headers=self.headers, params=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(e)

    def sendSurvey(self):
        with open(f"{THIS_FOLDER}/students.json", "r") as f:
            students = json.load(f)
            if len(students) == 0:
                return
            sender_email = "treythomas93.tutor@gmail.com"
            message = MIMEMultipart("alternative")
            message["Subject"] = "Post Tutoring Session Survey"
            message["From"] = sender_email
            with open(f"{THIS_FOLDER}/index.html", "r", encoding='utf-8') as html_file:
                message.attach(MIMEText(html_file.read(), "html"))
                port = 465  # For SSL
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
                    server.login(sender_email, PASSWORD)

                    for student in students:
                        time_to_send = datetime.strptime(
                            student["time_to_send"], '%Y-%m-%dT%H:%M:%S.%fZ')
                        if time_to_send <= datetime.utcnow():
                            receiver_email = student["email"]
                            message["To"] = receiver_email
                            uuid = student["uuid"]
                            # SEND SURVEY VIA EMAIL
                            server.sendmail(
                                sender_email, receiver_email, message.as_string())
                            log = f"MESSAGE SENT [{datetime.utcnow()}] Student: {student['name']} - Email: {student['email']}\n"
                            print(log)
                            with open(f"{THIS_FOLDER}/logs/sent.log", "a") as f:
                                f.write(log)
                            # REMOVE STUDENT FROM students.json
                            with open(f"{THIS_FOLDER}/students.json", "w") as f:
                                students = [student for student in students if student["uuid"] != uuid]
                                f.write(json.dumps(students, indent=4))

if __name__ == "__main__":
    sender = SurveySender()
    if SEND_SURVEY:
        sender.sendSurvey()
    sessions = sender.getSessions()
    students = sender.getStudents(sessions)
    sender.saveStudents(students)
