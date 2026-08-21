from fastapi import APIRouter

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/crash")
def crash():
    # Intentionally unhandled: exercises the centralized exception handler
    # and the "unhandled_exception" log event (see app/main.py).
    raise RuntimeError("Intentional crash for SOC training: unhandled exception scenario")
