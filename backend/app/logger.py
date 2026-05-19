import sys
import os
import logging
from loguru import logger
from logtail import LogtailHandler

_BASE = os.path.dirname(os.path.dirname(__file__))
LOG_FILE = os.path.join(_BASE, "logs", "app.log")

BETTERSTACK_TOKEN = "fsQKvh1mkpNwgHuYXnckuu7G"
BETTERSTACK_HOST  = "https://s2451040.eu-fsn-3.betterstackdata.com"

# Remove default loguru handler
logger.remove()

# Console — human-readable, colored
logger.add(
    sys.stdout,
    level="DEBUG",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[event]}</cyan> | "
        "{message}"
    ),
    filter=lambda r: "event" in r["extra"],
)

# Console fallback for logs without 'event' key
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    filter=lambda r: "event" not in r["extra"],
)

# File — structured, rotates daily, keeps 30 days
logger.add(
    LOG_FILE,
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra} | {message}",
    rotation="00:00",
    retention="30 days",
    encoding="utf-8",
)

# Betterstack — ship all logs to the cloud dashboard
_bt_handler = LogtailHandler(
    source_token=BETTERSTACK_TOKEN,
    host=BETTERSTACK_HOST,
)
_bt_handler.setLevel(logging.DEBUG)

# Bridge: loguru → stdlib logging → Betterstack handler
class _InterceptHandler(logging.Handler):
    def emit(self, record):
        pass  # handled below via loguru sink

def _betterstack_sink(message):
    record = message.record
    log_entry = {
        "dt": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        **record["extra"],
    }
    bt_logger = logging.getLogger("helmet_detection")
    bt_logger.addHandler(_bt_handler)
    bt_logger.setLevel(logging.DEBUG)
    level = getattr(logging, record["level"].name, logging.INFO)
    bt_logger.log(level, record["message"], extra={"context": record["extra"]})

logger.add(_betterstack_sink, level="DEBUG")
