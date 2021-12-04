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
from assets.datetime_tz import datetimeTZ
import logging
from assets.exception_handler import exception_handler
from assets.timeformatter import Formatter
from assets.multifilehandler import MultiFileHandler
from assets.pushsafer import PushNotification

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

load_dotenv(dotenv_path=f"{THIS_FOLDER}/config.env")

API_TOKEN = os.getenv("API_TOKEN")
PASSWORD = os.getenv("PASSWORD")
SEND_SURVEY = True if os.getenv("SEND_SURVEY") == "True" else False


class SurveySender:

    def __init__(self):
        self.base_url = "https://api.calendly.com"
        self.headers = {
            'Content-Type': "application/json",
            'Authorization': f"Bearer {API_TOKEN}"
        }
        self.user_uuid = "3ab7508f-1a22-4b83-9373-683b8f4d771e"
        self.need_to_send_path = f"{THIS_FOLDER}/need_to_send.json"
        if not os.path.exists(self.need_to_send_path):
            with open(self.need_to_send_path, "w") as f:
                f.write(json.dumps([]))
        with open(self.need_to_send_path, "r") as f:
            self.need_to_send = json.load(f)
        with open(f"{THIS_FOLDER}/index.html", "r", encoding='utf-8') as html_file:
            self.html_file = html_file.read()

        # INSTANTIATE LOGGER
        file_handler = MultiFileHandler(
            filename=f'{os.path.abspath(os.path.dirname(__file__))}/logs/error.log', mode='a')

        formatter = Formatter('%(asctime)s [%(levelname)s] %(message)s')

        file_handler.setFormatter(formatter)

        ch = logging.StreamHandler()

        ch.setLevel(level="INFO")

        ch.setFormatter(formatter)

        self.logger = logging.getLogger(__name__)

        self.logger.setLevel(level="INFO")

        self.logger.addHandler(file_handler)

        self.logger.addHandler(ch)

        self.push_notification = PushNotification(self.logger)

    @exception_handler
    def getSessions(self):
        """gets sessions for user

        [extended_summary]

        Returns:
            [list]: [all sessions for user]
        """
        url = f"{self.base_url}/scheduled_events"
        payload = {
            "user": f"{self.base_url}/users/{self.user_uuid}",
            "min_start_time": datetime.utcnow(),
            "max_start_time": datetime.utcnow() + timedelta(hours=6),
            "status": "active"
        }

        return self.sendRequest(url, payload)

    @exception_handler
    def getStudents(self, sessions):
        """get student for each session

        [extended_summary]

        Args:
            sessions ([list]): [all sessions for user]

        Returns:
            [list]: [dictionaries containing student data]
        """
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
            if invitees != None:
                obj["name"] = invitees["collection"][0]["name"]
                obj["email"] = invitees["collection"][0]["email"]
                obj["uuid"] = invitees["collection"][0]["uri"].split(
                    "/")[-1].strip()
                students.append(obj)

        return students

    @exception_handler
    def saveStudents(self, students):
        """save student data to need_to_send.json file. This file data will be used to send survey's to emails.

        [extended_summary]

        Args:
            students ([list]): [dictionaries containing student data]
        """
        saved_uuid = [student["uuid"] for student in self.need_to_send]
        students = [*self.need_to_send, *
                    [student for student in students if student["uuid"] not in saved_uuid]]
        with open(self.need_to_send_path, "w") as f:
            f.write(json.dumps(students, indent=4))

    @exception_handler
    def sendRequest(self, url, payload=None):
        """handle requests

        [extended_summary]

        Args:
            url ([type]): [url of request]
            payload ([type], optional): [specifies data to be fetched]. Defaults to None.

        Returns:
            [json, None]: [json from response or None if exception]
        """
        try:
            response = requests.get(url, headers=self.headers, params=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(e)
            self.push_notification.send(e)
            return None

    @exception_handler
    def sendSurvey(self):
        """send survey to students whose time_to_send value is less than current utc time

        [extended_summary]
        """
        students = self.need_to_send
        if len(students) == 0:
            return
        sender_email = "treythomas93.tutor@gmail.com"
        message = MIMEMultipart("alternative")
        message["Subject"] = "Post Tutoring Session Survey"
        message["From"] = sender_email
        message.attach(MIMEText(self.html_file, "html"))
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
                    if SEND_SURVEY:
                        server.sendmail(
                            sender_email, receiver_email, message.as_string())
                        log = f"SURVEY SENT - Student: {student['name']} - Email: {student['email']}"
                        self.logger.info(log)
                        self.push_notification.send(log)
                        # REMOVE STUDENT FROM students.json
                        with open(self.need_to_send_path, "w") as f:
                            students = [
                                student for student in students if student["uuid"] != uuid]
                            f.write(json.dumps(students, indent=4))


if __name__ == "__main__":
    def canRun():
        """determine if program should run based on time of day and day of week.

        [extended_summary]
        """
        dt = datetimeTZ()

        day = dt.strftime("%a")
        tm = dt.strftime("%H:%M:%S")
        weekends = ["Sat", "Sun"]

        if tm > "17:00" or tm < "06:00" or day in weekends:
            return False
        return True

    try:
        if canRun():
            sender = SurveySender()
            sessions = sender.getSessions()
            if sessions != None:
                students = sender.getStudents(sessions)
                sender.saveStudents(students)
            sender.sendSurvey()
    except Exception as e:
        print(e)
