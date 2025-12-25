from src.schemas.ncm import NcmResponse
from src.schemas.general import Pagination
from asyncpg import Connection


async def search_ncms(q: str, uf: str, limit: int, offset: int, conn: Connection) -> Pagination[NcmResponse]:
    if not q:
        sql = """
            SELECT 
                * 
            FROM 
                fiscal_ncms 
            WHERE 
                uf = $1
            ORDER BY 
                code
            LIMIT 
                $2 
            OFFSET 
                $3
        """
        rows = await conn.fetch(sql, uf.upper(), limit, offset)        
        total = await conn.fetchval("SELECT COUNT(*) FROM fiscal_ncms WHERE uf = $1", uf.upper())
    else:
        clean_q = q.replace(".", "").strip()
        sql = """
            SELECT * FROM (
                SELECT * FROM fiscal_ncms 
                WHERE uf = $1 AND code ILIKE $2
                
                UNION
                
                SELECT * FROM fiscal_ncms 
                WHERE uf = $1 AND immutable_unaccent(description) ILIKE immutable_unaccent($3)
            ) AS combined_results
            ORDER BY code
            LIMIT $4 OFFSET $5
        """
        rows = await conn.fetch(
            sql, 
            uf.upper(), 
            f"{clean_q}%",
            f"%{q}%",
            limit, 
            offset
        )        

        count_sql = """
            SELECT COUNT(*) FROM (
                SELECT code FROM fiscal_ncms WHERE uf = $1 AND code ILIKE $2
                UNION
                SELECT code FROM fiscal_ncms WHERE uf = $1 AND immutable_unaccent(description) ILIKE immutable_unaccent($3)
            ) AS total_count
        """
        total = await conn.fetchval(count_sql, uf.upper(), f"{clean_q}%", f"%{q}%")
    

    return Pagination(
        total=total,
        limit=limit,
        offset=offset,
        results=[NcmResponse(**dict(row)) for row in rows]
    )
    
    
async def get_ncm_by_code(code: str, uf: str, conn: Connection) -> NcmResponse:
    clean_code = code.replace(".", "").strip()
    row = await conn.fetchrow(
        """
        SELECT 
            * 
        FROM 
            fiscal_ncms 
        WHERE 
            code = $1 
            AND uf = $2
        """,
        clean_code, uf.upper()
    )
    
    return NcmResponse(**dict(row)) if row else None