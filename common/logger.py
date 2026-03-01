import logging

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[94m",     # Blue
        logging.INFO: "\033[92m",      # Green
        logging.WARNING: "\033[93m",   # Yellow
        logging.ERROR: "\033[91m",     # Red
        logging.CRITICAL: "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, fmt=None, datefmt=None, prefix=""):
        super().__init__(fmt, datefmt)
        self.prefix = prefix

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        msg = super().format(record)
        return f"{color}{self.prefix} {msg}{self.RESET}"


def get_logger(name: str, prefix: str):
    """
    Returns a logger with a custom prefix and color formatting.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:  # avoid duplicate handlers
        handler = logging.StreamHandler()
        formatter = ColorFormatter('%(asctime)s %(levelname)s: %(message)s',
                                   datefmt='%H:%M:%S', prefix=prefix)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger