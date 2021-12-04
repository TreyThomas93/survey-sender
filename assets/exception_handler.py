# EXCEPTION HANDLER DECORATOR FOR HANDLER EXCEPTIONS AND LOGGING THEM
import traceback


def exception_handler(func):
    def wrapper(self, *args, **kwargs):
        logger = self.logger
        try:
            return func(self, *args, **kwargs)
        except Exception:
            logger.error(traceback.format_exc())
            self.push_notification.send(traceback.format_exc())
    return wrapper
