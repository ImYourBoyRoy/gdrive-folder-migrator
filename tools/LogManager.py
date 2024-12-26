# tools/LogManager.py
import logging
from pathlib import Path

class LogManager:
    def __init__(self, log_path: str, log_level: str):
        self.log_path = log_path
        self.log_level = getattr(logging, log_level.upper())
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        # Configure basic logging
        logging.basicConfig(
            filename=self.log_path,
            level=self.log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Create logger instance
        logger = logging.getLogger(__name__)

        # Add console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        return logger

    def get_logger(self) -> logging.Logger:
        return self.logger