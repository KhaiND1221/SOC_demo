import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.logging_config import app_logger, log_event
from app.request_context import request_id_var, session_id_var, source_ip_var, user_id_var


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Establishes per-request correlation context and emits one generic
    http_request access-style log line per request (method/path/status/
    duration) in addition to the specific business-event logs emitted by
    route handlers. request_id is taken from the X-Request-ID header set
    by Nginx ($request_id) when present, so the same id ties together the
    Nginx access log line and every app/auth log line for that request."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        source_ip = (
            request.headers.get("X-Real-IP")
            or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (request.client.host if request.client else None)
        )

        # Note: deliberately no reset()/finally here. FastAPI wires the
        # catch-all Exception handler into Starlette's ServerErrorMiddleware,
        # which sits OUTSIDE this middleware in the stack (unlike
        # RequestValidationError, handled by the inner ExceptionMiddleware).
        # If an unhandled exception propagates out of call_next, resetting
        # these contextvars here would erase request_id/source_ip before
        # the outer handler in app/main.py gets to log and return them.
        # Each request runs in its own asyncio Task with its own copied
        # context, so skipping reset() does not leak values across requests.
        request_id_var.set(request_id)
        source_ip_var.set(source_ip)
        user_id_var.set(None)
        session_id_var.set(None)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        log_event(
            app_logger,
            event="http_request",
            level="info",
            result="success" if response.status_code < 400 else "fail",
            message=f"{request.method} {request.url.path} -> {response.status_code}",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response
