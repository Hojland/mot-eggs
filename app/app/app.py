import sentry_sdk
from fastapi import FastAPI, Request
from loguru import logger
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from settings import settings
from utils import log
from v1.app import app as v1_app

try:
    import toml

    pyproj_dct = toml.load("pyproject.toml")
    version = pyproj_dct["tool"]["poetry"]["version"]
    description = pyproj_dct["tool"]["poetry"]["description"]
except Exception:
    version = "v0.1.0"
    description = "Multiple object tracking of easter eggs in an app"

app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs",
    redoc_url="/",
    description=description,
    version=version,
    openapi_url="/openapi.json",
    contact={
        "name": "Martin Højland Hansen",
        "email": "hojland93@gmail.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

log.setup_logging(
    cloud_logging=bool(settings.CLOUD_LOGGING == "true")
)  # Set cloud logging to false when testing locally to reduce quota usage

if settings.ENVIRONMENT != "development":
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1 / 100,
    )

logger.info("I'm starting up")


app.include_router(
    v1_app,
    prefix="/v1",
    tags=["v1"],
)
app.add_middleware(SentryAsgiMiddleware)

"""
%load_ext autoreload
%autoreload 2
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
