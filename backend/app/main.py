import traceback

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import Base, engine, wait_for_db
from app.logging_config import app_logger, log_event
from app.middleware import RequestContextMiddleware
from app.request_context import request_id_var
from app.routers import auth, debug, profile, tasks

app = FastAPI(title="Task Manager API")

app.add_middleware(RequestContextMiddleware)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(tasks.router)
app.include_router(debug.router)


@app.on_event("startup")
def on_startup():
    wait_for_db()
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    log_event(
        app_logger,
        event="validation_error",
        level="warning",
        result="fail",
        message="Request validation failed",
        path=request.url.path,
        errors=exc.errors(),
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Validation error", "request_id": request_id_var.get()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Full stack trace goes to the server-side log only; the client only
    # ever sees a generic message + request_id (correlate the two here).
    log_event(
        app_logger,
        event="unhandled_exception",
        level="error",
        result="fail",
        message=f"Unhandled exception: {exc}",
        path=request.url.path,
        exception_type=type(exc).__name__,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "request_id": request_id_var.get()},
    )
