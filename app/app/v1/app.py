

from fastapi import APIRouter, Response, status

router = APIRouter()


@router.get(path="/readyz", include_in_schema=False)
def readyz(response: Response):
    ready = True
    response.status_code = status.HTTP_200_OK if ready else 503  # service unavailable
    return response


@router.get(path="/livez", include_in_schema=False)
def livez(response: Response):
    ready = True
    response.status_code = status.HTTP_200_OK if ready else 503  # service unavailable
    return 