from fastapi import APIRouter, Depends, Path
from fastapi_limiter.depends import RateLimiter
from src.schemas.companies import CompanyResponse
from src.security import get_postgres_connection
from asyncpg import Connection
from src.services import companies as companies_service


CACHE_TTL_DAYS = 30


router = APIRouter(dependencies=[Depends(RateLimiter(times=32, seconds=60))])


@router.get("/{cnpj:path}", response_model=CompanyResponse)
async def get_company(    
    cnpj: str = Path(..., title="CNPJ", description="CNPJ somente números"),
    conn: Connection = Depends(get_postgres_connection)
) -> CompanyResponse:
    return await companies_service.get_company(cnpj, conn)