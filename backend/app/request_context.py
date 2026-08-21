import contextvars
from typing import Optional

# Per-request state, set by RequestContextMiddleware and enriched by
# get_current_user() once a session is resolved. Read by the JSON log
# formatter's ContextFilter so every log line emitted during a request
# automatically carries request_id/source_ip/user_id/session_id without
# every call site having to pass them explicitly.
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
source_ip_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("source_ip", default=None)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)
session_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("session_id", default=None)
