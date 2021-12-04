from datetime import datetime
import logging
from assets.datetime_tz import datetimeTZ


class Formatter(logging.Formatter):
    """override logging.Formatter to use an naive datetime object"""

    def formatTime(self, record, datefmt=None):
        return datetimeTZ()
