

import base64
from typing import cast

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from settings import settings

auth = HTTPBearer()


async def is_authenticated(request: Request, access_token=cast(HTTPAuthorizationCredentials, Depends(auth))):
    try:
        decoded_token = jwt.decode(
            access_token.credentials, base64.b64decode(settings.JWT_PUBLIC_KEY), algorithms=[settings.JWT_ALGORITHM]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect API token",
        )
    return {"decoded_token": decoded_token, "access_token": access_token}