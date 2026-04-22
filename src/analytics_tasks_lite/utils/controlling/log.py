# %% Controlling
import sys
import logging
from datetime import datetime
import getpass


def log_start(folder_location):
    """Start logging process"""

    global file_handler, __log_name

    # --- NEW ADDITION: Ensure the directory exists ---
    # This creates the 'log' folder if it doesn't exist. 
    # parents=True ensures it creates nested folders if needed.
    # exist_ok=True prevents an error if the folder already exists.
    folder_location.mkdir(parents=True, exist_ok=True)
    # ------------------------------------------------

    # Check if the logger is already set up
    if "file_handler" in globals() and file_handler is not None:
        print(
            "\nWARNING : Logging is already in progress. Call log_end() before starting a new log."
        )
        return

    class LogPrints:
        def __init__(self, logger, level=logging.INFO):
            self.logger = logger
            self.level = level
            self.linebuf = ""

        def write(self, buf):
            self.linebuf += buf
            lines = self.linebuf.split("\n")
            for line in lines[:-1]:
                self.logger.log(self.level, line)
            self.linebuf = lines[-1]

        def flush(self):
            pass

    # Define file_dt globally for demonstration purposes
    file_dt = datetime.now().strftime("%Y%m%d_%H%M%S")

    _log_name = "log_" + file_dt + ".log"
    __log_name = folder_location / _log_name

    # Create a logger only if it doesn't exist
    if "logger" not in globals():
        logger = logging.getLogger(str(getpass.getuser()))
        logger.setLevel(logging.DEBUG)

        # Create a console handler and set the level to DEBUG
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # Removes previously set handlers
        logger.handlers = []

        # Create a file handler and add it to the logger
        file_handler = logging.FileHandler(__log_name, "w+", encoding="utf-8")

        # Formatting
        formatter = logging.Formatter(
            "%(asctime)s | [%(levelname)s] | %(name)s | %(message)s"
        )
        file_handler.setFormatter(formatter)

        formatter_console = logging.Formatter("%(message)s")
        console_handler.setFormatter(formatter_console)

        # Add the handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # Redirect prints to the log
        sys.stdout = LogPrints(logger, level=logging.INFO)
        sys.stderr = LogPrints(logger, level=logging.ERROR)

        print("\n✅ NOTE: Logging started...", __log_name)
    else:
        print("\n☑️  NOTE: Logging is already in progress.")

## log_end
def log_end():
    """end logging process"""
    global file_handler

    if file_handler is not None:
        print("☑️  NOTE: Logging ended...", __log_name)
        # logger.info('NOTE: Logging ended...', __log_name)

        # Close the file handler (this will also flush the log entries to the file)
        file_handler.flush()
        file_handler.close()

        # Reset stdout and stderr to their original values
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        # Set file_handler to None to indicate that logging is not in progress
        file_handler = None
    else:
        print("\nNOTE: Logging is not in progress. No action taken.")
