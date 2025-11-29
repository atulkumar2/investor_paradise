import io
import logging
import os
import sys

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
        isinstance(h, logging.FileHandler) and getattr(
          h, "baseFilename", None
          ) and os.path.basename(h.baseFilename) == os.path.basename(_LOG_FILE)
        for h in logger.handlers
    )
    if not has_file:
        fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s %(name)s:%(lineno)s %(levelname)s:%(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    # Attach a stream handler that safely writes UTF-8 (replace unencodable chars).
    has_stream = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    if not has_stream:
        # Wrap the stdout buffer with a TextIOWrapper that encodes to utf-8 and replaces errors.
        try:
            utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, 
                          encoding="utf-8", errors="replace", line_buffering=True)
            sh = logging.StreamHandler(stream=utf8_stdout)
        except Exception:
            # Fallback to default StreamHandler if wrapping fails.
            sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter(
          "%(asctime)s %(name)s:%(lineno)s %(levelname)s:%(message)s"))
        # Keep a reference so the wrapper isn't garbage-collected.
        if hasattr(sh, "stream"):
            sh._utf8_stream = getattr(sh, "stream")
        logger.addHandler(sh)

    return logger


print("✅ Logging configured")
