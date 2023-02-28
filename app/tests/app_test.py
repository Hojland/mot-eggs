import asyncio
import os

import pytest
from httpx import AsyncClient

from app import app

SAGA_TOKEN = os.environ.get("SAGA_TOKEN", None)


async def fetch(url, params: dict, mail_path: str, token: str):
    async with AsyncClient(app=app) as client:
        response = await client.post(
            url,
            files={"mail": open(mail_path, "rb")},
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
    return response


@pytest.mark.asyncio
async def test_app_coros(random_email_path):
    params = {}
    url = "http://test/docs"
    coros = (fetch(url, params, mail_path=random_email_path, token=SAGA_TOKEN) for _ in range(4))
    responses = await asyncio.gather(*coros)
    for response in responses:
        assert response.status_code == 200
