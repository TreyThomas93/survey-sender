import pytz
import os
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
root = Path(THIS_FOLDER).parent

load_dotenv(dotenv_path=f"{root}/config.env")
TIMEZONE = os.getenv("TIMEZONE")


def datetimeTZ():
    dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)
    dt = dt.astimezone(pytz.timezone(TIMEZONE))
    return datetime.strptime(dt.strftime(
        "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
