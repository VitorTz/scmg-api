from fastapi import APIRouter, Depends, Path
from fastapi_limiter.depends import RateLimiter
from src.schemas.companies import CompanyResponse
from src.security import get_postgres_connection
from src.services import companies as companies_service
from src.services.redis_client import RedisService
from src.util import remove_non_digits
from asyncpg import Connection


TTL = 3600 * 3


router = APIRouter(dependencies=[Depends(RateLimiter(times=32, seconds=60))])


@router.get("/{cnpj:path}", response_model=CompanyResponse)
async def get_company(    
    cnpj: str = Path(..., title="CNPJ", description="CNPJ somente números"),
    conn: Connection = Depends(get_postgres_connection)
) -> CompanyResponse:
    return await RedisService.get_or_set_cache(
        f"cnpjs:{remove_non_digits(cnpj)}", 
        CompanyResponse, 
        lambda : companies_service.get_company(cnpj, conn),
        ttl=TTL
    )
