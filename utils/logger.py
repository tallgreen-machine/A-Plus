import logging
import sys

def setup_logger():
    """
    Sets up a centralized logger for the application.
    """
    logger = logging.getLogger('Trad')
    logger.setLevel(logging.INFO)

    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create a handler for stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    if not logger.handlers:
        logger.addHandler(stream_handler)

    return logger

# Create a logger instance to be imported by other modules
log = setup_logger()
