from src.schemas.ncm import NcmResponse
from src.schemas.general import Pagination
from asyncpg import Connection



async def search_ncms(
    q: str,
    limit: int, 
    offset: int, 
    conn: Connection
) -> Pagination[NcmResponse]:
    rows = await conn.fetch("SELECT * FROM search_ncms_optimized($1, $2, $3)", q, limit, offset)
    
    if not rows:
        return Pagination(
            total=0,
            limit=limit,
            offset=offset,
            results=[]
        )
    
    return Pagination(
        total=rows[0]['total_count'],
        limit=limit,
        offset=offset,
        results=[NcmResponse(**dict(row)) for row in rows]
    )
    
    
async def get_ncm_by_code(code: str, conn: Connection) -> NcmResponse:
    clean_code = code.replace(".", "").strip()
    row = await conn.fetchrow(
        """
        SELECT 
            * 
        FROM 
            fiscal_ncms 
        WHERE 
            code = $1
        """,
        clean_code
    )
    
    return NcmResponse(**dict(row)) if row else None