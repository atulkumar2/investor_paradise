"""Logging configuration for Investor Agent."""

import io
import logging
import os
import sys

# Clean up any previous logs
for log_file in ["logger.log", "web.log", "tunnel.log"]:
    if os.path.exists(log_file):
        os.remove(log_file)
        print(f"🧹 Cleaned up {log_file}")

_LOG_FILE = "investor_agent_logger.log"

# Configure root logging to write to the log file if not already configured.
# This captures ALL logs including ADK, Google GenAI, and third-party libraries.
if not logging.getLogger().handlers:
    logging.basicConfig(
        filename=_LOG_FILE,
        level=logging.INFO,  # Set to INFO to avoid excessive DEBUG from libraries
        format="%(asctime)s - %(levelname)s - %(name)s:%(lineno)s - %(message)s",
    )
else:
    # If handlers exist, ensure root logger writes to our file too
    root_logger = logging.getLogger()
    has_root_file = any(
        isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None)
        and os.path.basename(h.baseFilename) == os.path.basename(_LOG_FILE)
        for h in root_logger.handlers
    )
    if not has_root_file:
        root_fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        root_fh.setLevel(logging.INFO)
        root_fh.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s:%(lineno)s - %(message)s"
        ))
        root_logger.addHandler(root_fh)
        root_logger.setLevel(logging.INFO)


def get_logger(name: str):
    """Return a configured logger for `name`.

    Ensures a `FileHandler` is attached exactly once so repeated imports
    don't create duplicate handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Unified formatter for both file and stream handlers.
    fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s:%(lineno)s - %(message)s"
    )

    # Ensure consistent formatting and avoid duplicate propagation to root.
    has_file = any(
        isinstance(h, logging.FileHandler)
        and getattr(h, "baseFilename", None)
        and os.path.basename(h.baseFilename) == os.path.basename(_LOG_FILE)
        for h in logger.handlers
    )
    if not has_file:
        fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    # Attach a stream handler that safely writes UTF-8 (replace not encodable chars).
    has_stream = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    if not has_stream:
        # Wrap stdout buffer with TextIOWrapper that encodes to utf-8 and replaces errors
        try:
            utf8_stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
            )
            sh = logging.StreamHandler(stream=utf8_stdout)
        except (AttributeError, LookupError, ValueError, OSError):
            # Fallback to default StreamHandler if wrapping fails.
            sh = logging.StreamHandler()
        # Configure stream handler consistently
        sh.setLevel(logging.INFO)
        sh.setFormatter(fmt)
        # StreamHandler holds the stream; no extra reference needed.
        logger.addHandler(sh)

    # Prevent logs from this logger being written again by the root handlers.
    logger.propagate = False

    return logger


print("✅ Logging configured")
