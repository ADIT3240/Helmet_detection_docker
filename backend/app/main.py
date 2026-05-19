import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .logger import logger

app = FastAPI(title="Helmet Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    client_ip = request.client.host if request.client else "unknown"

    # Skip noisy status polling from detailed logs — log it at DEBUG only
    is_status_poll = request.url.path.startswith("/api/status/")

    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000)

        log_fn = logger.debug if is_status_poll else logger.info
        log_fn(
            f"{request.method} {request.url.path} → {response.status_code} ({duration_ms}ms)",
            event="http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
        )
        return response

    except Exception as exc:
        duration_ms = round((time.time() - start) * 1000)
        logger.exception(
            f"{request.method} {request.url.path} → UNHANDLED ERROR ({duration_ms}ms)",
            event="http_error",
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
            client_ip=client_ip,
            error=str(exc),
        )
        raise


@app.get("/health")
def health():
    return {"status": "ok"}
