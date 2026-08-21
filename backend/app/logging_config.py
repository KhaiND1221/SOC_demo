import json
import logging
import logging.handlers
import os
from datetime import datetime, timezone

from app.config import settings
from app.request_context import request_id_var, session_id_var, source_ip_var, user_id_var

LOG_DIR = "/var/log/app"


class ContextFilter(logging.Filter):
    """Injects the current request's correlation fields into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.source_ip = source_ip_var.get()
        record.user_id = user_id_var.get()
        record.session_id = session_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "source_ip": getattr(record, "source_ip", None),
            "user_id": getattr(record, "user_id", None),
            "session_id": getattr(record, "session_id", None),
            "result": getattr(record, "result", None),
        }

        # Event-specific fields (e.g. order_id, changed_fields, reason)
        # override the generic context fields above when both are present
        # (e.g. register/login events set user_id explicitly before any
        # session exists yet).
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def _build_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level.upper())
    logger.propagate = False

    formatter = JsonFormatter()
    context_filter = ContextFilter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(context_filter)
    logger.addHandler(stream_handler)

    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, filename), maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)
    logger.addHandler(file_handler)

    return logger


# Two distinct, purpose-separated loggers, per the lab design:
#  - app_logger  -> /var/log/app/app.log   (business/application events)
#  - auth_logger -> /var/log/app/auth.log  (authentication-specific events)
# Auth-related actions (login/logout) are intentionally logged to BOTH:
# once as a generic app event (login_success/login_fail/logout) and once
# as an uppercase auth-layer event (LOGIN_SUCCESS/LOGIN_FAIL/LOGOUT/
# ACCOUNT_LOCKED/SESSION_EXPIRED) with richer auth-specific fields. This
# gives two independent data sources to correlate, by design.
app_logger = _build_logger("app", "app.log")
auth_logger = _build_logger("auth", "auth.log")


def log_event(
    logger: logging.Logger,
    event: str,
    level: str = "info",
    result: str = "success",
    message: str = "",
    **fields,
) -> None:
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(
        message or event,
        extra={"event": event, "result": result, "extra_fields": fields},
    )
