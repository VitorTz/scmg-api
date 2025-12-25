from fastapi import APIRouter, Depends, status
from fastapi_limiter.depends import RateLimiter
from src.schemas.currency import Currency
from src.security import get_postgres_connection
from asyncpg import Connection
from src.services import currency as currency_service


router = APIRouter(dependencies=[Depends(RateLimiter(times=32, seconds=60))])


@router.get("/", status_code=status.HTTP_200_OK, response_model=Currency)
async def get_currencies(conn: Connection = Depends(get_postgres_connection)):
    return await currency_service.get_currencies(conn)