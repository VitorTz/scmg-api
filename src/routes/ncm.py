from fastapi import Depends, Query, APIRouter, status, Path
from fastapi_limiter.depends import RateLimiter
from src.security import get_postgres_connection
from src.schemas.ncm import NcmResponse
from src.schemas.general import Pagination
from src.services import ncm as ncm_service
from asyncpg import Connection
from typing import Optional


router = APIRouter(dependencies=[Depends(RateLimiter(times=32, seconds=60))])


@router.get(
    "/", 
    status_code=status.HTTP_200_OK,
    response_model=Pagination[NcmResponse]
)
async def search_ncms(
    q: Optional[str] = Query(None, description="Busca por Código ou Descrição (ex: 'Cerveja' ou '2203')"),
    uf: str = Query(default='SC', min_length=2, max_length=2, description="UF obrigatória (ex: SC)"),
    limit: int = Query(default=64, ge=0, le=64),
    offset: int = Query(default=0, ge=0),
    conn: Connection = Depends(get_postgres_connection)
):
    return await ncm_service.search_ncm(q, uf, limit, offset, conn)


@router.get("/{code}", response_model=NcmResponse)
async def get_ncm_by_code(
    code: str = Path(..., description="Código NCM (apenas números)"),
    uf: str = Query(default='SC', min_length=2, max_length=2),
    conn: Connection = Depends(get_postgres_connection)
):
    return await ncm_service.get_ncm_by_code(code, uf, conn)