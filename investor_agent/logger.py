import logging
import os

# Clean up any previous logs
for log_file in ["logger.log", "web.log", "tunnel.log"]:
    if os.path.exists(log_file):
        os.remove(log_file)
        print(f"🧹 Cleaned up {log_file}")

_LOG_FILE = "logger.log"

# Configure root logging to write to the log file if not already configured.
if not logging.getLogger().handlers:
    logging.basicConfig(
        filename=_LOG_FILE,
        level=logging.DEBUG,
        format="%(asctime)s %(name)s:%(lineno)s %(levelname)s:%(message)s",
    )


def get_logger(name: str):
    """Return a configured logger for `name`.

    Ensures a `FileHandler` is attached exactly once so repeated imports
    don't create duplicate handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Attach a file handler if logger has no handlers that write to our file.
    has_file = any(
        isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) and os.path.basename(h.baseFilename) == os.path.basename(_LOG_FILE)
        for h in logger.handlers
    )
    if not has_file:
        fh = logging.FileHandler(_LOG_FILE)
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s %(name)s:%(lineno)s %(levelname)s:%(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


print("✅ Logging configured")