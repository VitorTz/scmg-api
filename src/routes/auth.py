from fastapi import APIRouter, Depends, status, Response, Cookie
from fastapi_limiter.depends import RateLimiter
from src.security import get_postgres_connection, get_rls_connection
from src.schemas.auth import LoginRequest
from src.schemas.user import UserResponse
from src.schemas.rls import RLSConnection
from src.model import user as user_model
from src.services import auth as auth_service
from typing import Optional
from asyncpg import Connection


router = APIRouter(dependencies=[Depends(RateLimiter(times=16, seconds=60))])


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse
)
async def get_me(rls: RLSConnection = Depends(get_rls_connection)):
    return await user_model.get_user_by_id(rls.user['id'], rls.conn)


@router.post(
    "/login", 
    status_code=status.HTTP_200_OK, 
    response_model=UserResponse
)
async def login(
    login_req: LoginRequest,
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
    conn: Connection = Depends(get_postgres_connection)
):    
    return await auth_service.login(login_req, refresh_token, response, conn)


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK, 
    response_model=UserResponse
)
async def refresh(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
    conn: Connection = Depends(get_postgres_connection)
):    
    return await auth_service.refresh(refresh_token, response, conn)


@router.post(
    "/logout", 
    status_code=status.HTTP_204_NO_CONTENT
)
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
    conn: Connection = Depends(get_postgres_connection)
):
    await auth_service.logout(refresh_token, response, conn)