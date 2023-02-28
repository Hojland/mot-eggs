

import logging
import os
import sys
from pprint import pformat
from typing import List

from loguru import logger

LOG_LEVEL = logging.getLevelName(os.environ.get("LOG_LEVEL", "DEBUG"))
JSON_LOGS = True if os.environ.get("JSON_LOGS", "0") == "1" else False


def no_api_slash_request_filter(record):
    return "GET / " not in record["message"] and 'readyz HTTP/1.1" 200' not in record["message"]


class InterceptHandler(logging.Handler):
    """
    Default handler from examples in loguru documentaion.
    See https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def format_record(record: dict) -> str:
    """
    Custom format for loguru loggers.
    Uses pformat for log any data like request/response body during debug.
    Works with logging if loguru handler it.
    Example:
    >>> payload = [{"users":[{"name": "Nick", "age": 87, "is_active": True}, {"name": "Alex", "age": 27, "is_active": True}], "count": 2}]
    >>> logger.bind(payload=).debug("users payload")
    >>> [   {   'count': 2,
    >>>         'users': [   {'age': 87, 'is_active': True, 'name': 'Nick'},
    >>>                      {'age': 27, 'is_active': True, 'name': 'Alex'}]}]
    """
    if record["extra"].get("x_mail_envelope_id") is not None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            + "<green>{extra[x_mail_envelope_id]}</green> | "
            + "<level>{level: <8}</level> | "
            + "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
    else:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            + "<level>{level: <8}</level> | "
            + "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )

    if record["extra"].get("payload") is not None:
        record["extra"]["payload"] = pformat(record["extra"]["payload"], indent=4, compact=True, width=88)
        format_string += " | <level>{extra[payload]}</level>"

    format_string += "{exception}\n"
    return format_string


def setup_logging(
    log_names: List[str] = [
        "uvicorn.error",
        "uvicorn.access",
        "uvicorn.asgi",
        "fastapi",
        "gunicorn.access",
        "gunicorn.error",
    ],
    cloud_logging: bool = True,
):
    # intercept everything at the root logger

    # remove every other logger's handlers
    # and propagate to root logger
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(
            name
        ).propagate = (
            False  # True (If True a lot of stuff also ends up in root handler - So is to be used if log_names is None TODO later)
        )

    # configure loguru
    if log_names:
        for name in log_names:
            logging.getLogger(name).handlers = [InterceptHandler()]
            logging.getLogger(name).setLevel(LOG_LEVEL)
    else:
        logging.root.handlers = [InterceptHandler()]  # logging.root.handlers = [InterceptHandler()]
        logging.root.setLevel(LOG_LEVEL)
    handlers = []
    if cloud_logging:
        import google.cloud.logging

        client = google.cloud.logging.Client()
        cloud_sink = client.get_default_handler()
        cloud_handler = {
            "sink": cloud_sink,
            "level": LOG_LEVEL,
            "format": format_record,
            "diagnose": False,
            "filter": no_api_slash_request_filter,
        }
        handlers.append(cloud_handler)
    else:
        sysout_handler = {
            "sink": sys.stdout,
            "level": LOG_LEVEL,
            "format": format_record,
            "diagnose": False,
            "filter": no_api_slash_request_filter,
        }
        handlers.append(sysout_handler)

    logger.remove()
    logger.configure(handlers=handlers)