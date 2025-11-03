import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TimerManager:
    def __init__(self):
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = datetime.now()

    def __exit__(self, *args):
        self.end_time = datetime.now()
        logger.info(f"Spends: {self.end_time - self.start_time}")
