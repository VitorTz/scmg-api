from asyncpg import Connection
from src.schemas.ncm import NcmResponse
from src.schemas.general import Pagination
from src.services.redis_client import RedisService
from fastapi.exceptions import HTTPException
from typing import Optional
from src.model import ncm as ncm_model


async def search_ncm(
    q: str,
    limit: int, 
    offset: int, 
    conn: Connection
):
    q_normalized = " ".join(q.strip().lower().split()) if q else "all"
    q_key = q_normalized.replace(" ", "_")
    
    key = f"ncm::{limit}:{offset}:{q_key}"
    
    return await RedisService.get_or_set_cache(
        key, 
        Pagination[NcmResponse], 
        lambda: ncm_model.search_ncms(q, limit, offset, conn)        
    )
    

async def get_ncm_by_code(code: str, conn: Connection) -> NcmResponse:
    ncm: Optional[NcmResponse] = await ncm_model.get_ncm_by_code(code, conn)

    if not ncm:
        raise HTTPException(status_code=404, detail=f"NCM {code} não encontrado")

    return ncm