from src.schemas.token import RefreshTokenCreate, RefreshToken
from asyncpg import Connection
from uuid import UUID


async def create_refresh_token(token: RefreshTokenCreate, conn: Connection) -> None:
    await conn.execute(
        """
            INSERT INTO refresh_tokens (
                id,
                user_id,
                expires_at,
                revoked,
                family_id                
            )
            VALUES
                ($1, $2, $3, $4, $5)
            RETURNING
                id
        """,
        token.token_id,
        token.user_id,
        token.expires_at,
        token.revoked,
        token.family_id        
    )
    
    
async def invalidate_token(token_id: UUID, replaced_by: UUID, conn: Connection) -> None:
    await conn.execute(
        """
            UPDATE 
                refresh_tokens 
            SET 
                revoked = TRUE, 
                replaced_by = $1
            WHERE 
                id = $2
        """, 
        replaced_by,
        token_id
    )
    
    
async def revoke_token_family(family_id: UUID, conn: Connection):
    await conn.execute(
        """
            UPDATE 
                refresh_tokens
            SET
                revoked = TRUE
            WHERE
                family_id = $1
                AND revoked = FALSE
        """,
        family_id
    )
    
async def revoke_token_family_by_token_id(token_id: UUID, conn: Connection):    
    await conn.execute(
        """
        UPDATE 
            refresh_tokens
        SET
            revoked = TRUE
        WHERE
            family_id = (
                SELECT 
                    family_id 
                FROM 
                    refresh_tokens 
                WHERE 
                    id = $1
            )
            AND revoked = FALSE
        """,
        token_id
    )
    
async def revoke_token_by_user_id(user_id: UUID, conn: Connection):    
    await conn.execute(
        """
        UPDATE 
            refresh_tokens
        SET
            revoked = TRUE
        WHERE
            user_id = $1
        """,
        user_id
    )
    
    
async def get_refresh_token_by_id(token_id: UUID | str, conn: Connection) -> RefreshToken:
    row = await conn.fetchrow(
        """
            SELECT 
                * 
            FROM 
                refresh_tokens 
            WHERE 
                id = $1
        """,
        token_id
    )
    
    return RefreshToken(**dict(row)) if row else None
