from fastapi import APIRouter

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/crash")
def crash():
    # Intentionally unhandled: for demoing/recording the "application
    # exception" log scenario (unhandled_exception_handler in main.py).
    # Not a real feature - never do this in a production route.
    raise RuntimeError("Intentional crash for demo/recording: unhandled exception scenario")
