from dotenv import load_dotenv
import requests
import os
from pathlib import Path

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

path = Path(THIS_FOLDER)

load_dotenv(dotenv_path=f"{path.parent}/config.env")

PUSH_API_KEY = os.getenv('PUSH_API_KEY')
DEVICE_ID = os.getenv('DEVICE_ID')


class PushNotification:

    def __init__(self, logger):
        self.url = 'https://www.pushsafer.com/api'
        self.post_fields = {
            "t": "Survey Sender",
            "m": None,
            "s": 0,
            "v": 1,
            "i": 1,
            "c": "#1E72E8",
            "d": DEVICE_ID,
            "ut": "Survey Sender",
            "k": PUSH_API_KEY,
        }
        self.logger = logger

    def send(self, notification):
        """ METHOD SENDS PUSH NOTIFICATION TO USER
        Args: 
            notification ([str]): MESSAGE TO BE SENT
        """
        try:
            # RESPONSE: {'status': 1, 'success': 'message transmitted', 'available': 983, 'message_ids': '18265430:34011'}
            self.post_fields["m"] = notification
            response = requests.post(self.url, self.post_fields)
            if response.json()["success"] == 'message transmitted':
                self.logger.info(f"Push Sent!")
            else:
                self.logger.warning(f"Push Failed!")
        except ValueError:
            pass
        except KeyError:
            pass
        except Exception as e:
            self.logger.error(e)