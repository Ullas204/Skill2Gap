import logging
import sys
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
_LOG_DIR = Path("logs")


def configure_logging() -> None:
    _LOG_DIR.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root_logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(_LOG_DIR / "app.log")
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root_logger.addHandler(file_handler)

    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(logging.WARNING)

    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    audit_handler = logging.FileHandler(_LOG_DIR / "audit.log")
    audit_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    audit_logger.addHandler(audit_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
