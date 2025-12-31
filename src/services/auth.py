from fastapi import status, Response
from fastapi.exceptions import HTTPException
from src.schemas.auth import LoginRequest
from src.schemas.tenant import TenantPublicInfo
from src.schemas.token import RefreshToken, AccessTokenCreate, RefreshTokenCreate, DecodedAccessToken
from src.schemas.user import LoginData, UserResponse, UserCreate, UserManagementContext
from src.schemas.rls import RLSConnection
from src.model import user as user_model
from src.model import refresh_token as refresh_token_model
from src.db.db import db_safe_exec, db
from src.constants import Constants
from datetime import datetime, timezone
from typing import Optional
from asyncpg import Connection
from src import security


INVALID_CREDENTIALS = HTTPException(
    detail="Email, CPF ou senha inválidos.",
    status_code=status.HTTP_401_UNAUTHORIZED
)


INVALID_REFRESH_TOKEN = HTTPException(
    detail="refresh_token inválido!",
    status_code=status.HTTP_401_UNAUTHORIZED
)


async def resolve_tenant_slug(slug: str, conn: Connection):
    row = await conn.fetchrow(
        "SELECT * FROM public_resolve_tenant_by_slug($1)",
        slug
    )
    
    if not row:
        raise HTTPException(404, "Loja não encontrada. Verifique o código.")
        
    return TenantPublicInfo(**row)


async def revoke_refresh_tokens(refresh_token: Optional[str], conn: Connection):
    if refresh_token:
        decoded = security.decode_refresh_token(refresh_token)
        await refresh_token_model.revoke_token_family_by_token_id(
            decoded.token_id,
            conn
        )

async def process_login_transaction(
    user_data: LoginData,
    refresh_token_create: RefreshTokenCreate,
    old_refresh_token_str: Optional[str],
    conn: Connection
):
    old_token_id = None
    if old_refresh_token_str:
        try:
            decoded = security.decode_refresh_token(old_refresh_token_str)
            old_token_id = decoded.token_id
        except Exception:
            pass
        
    await conn.execute(
        """
        -- [Passo 1] Configura Sessão (Para RLS funcionar nos passos seguintes)
        SELECT set_config('app.current_user_id', $1::text, true);
        SELECT set_config('app.current_user_tenant_id', $2::text, true);

        -- [Passo 2] Revoga Família de Tokens Antiga        
        UPDATE 
            refresh_tokens
        SET 
            revoked = TRUE
        WHERE 
            $3::uuid IS NOT NULL
            AND family_id = (
                SELECT 
                    family_id 
                FROM 
                    refresh_tokens 
                WHERE 
                    id = $3::uuid
            )
            AND revoked = FALSE;

        -- [Passo 3] Atualiza Último Login
        UPDATE 
            users 
        SET 
            last_login_at = CURRENT_TIMESTAMP 
        WHERE 
            id = $1::uuid;

        -- [Passo 4] Insere Novo Token
        INSERT INTO refresh_tokens (
            id,
            user_id,
            expires_at,
            revoked,
            family_id
        ) VALUES (
            $4::uuid, -- id do novo token
            $1::uuid, -- user_id
            $5,       -- expires_at
            $6,       -- revoked
            $7::uuid  -- family_id
        );
        """,
        user_data.id,
        user_data.tenant_id,
        old_token_id,
        refresh_token_create.token_id,
        refresh_token_create.expires_at,
        refresh_token_create.revoked,
        refresh_token_create.family_id
    )
    
    
async def login(
    login_req: LoginRequest,
    refresh_token: Optional[str],
    response: Response, 
    conn: Connection
) -> UserResponse:
        
    data: Optional[LoginData] = await db_safe_exec(user_model.get_login_data(login_req, conn))
    
    if not data: raise INVALID_CREDENTIALS
    
    if data.max_privilege_level == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não permitido."
        )
        
    if not security.verify_password(login_req.password, data.password_hash):
        raise INVALID_CREDENTIALS
    
    access_token_create: AccessTokenCreate = security.create_access_token(
        data.id,
        data.tenant_id
    )
    
    refresh_token_create: RefreshTokenCreate = security.create_refresh_token(data.id)                
    
    await process_login_transaction(data, refresh_token_create, refresh_token, conn)
    
    security.set_session_token_cookie(
        response, 
        access_token_create.jwt_token,
        access_token_create.expires_at,
        refresh_token_create.jwt_token,
        refresh_token_create.expires_at
    )
    
    return UserResponse(
        id=data.id,        
        name=data.name,
        nickname=data.nickname,
        email=data.email,
        roles=data.roles,        
        notes=data.notes,
        state_tax_indicator=data.state_tax_indicator,
        created_at=data.created_at,
        updated_at=data.updated_at,
        tenant_id=data.tenant_id,
        created_by=data.created_by,
        max_privilege_level=data.max_privilege_level
    )
    
    
async def refresh(
    refresh_token: Optional[str],
    response: Response,
    conn: Connection    
) -> UserResponse:
    if not refresh_token: 
        raise INVALID_REFRESH_TOKEN
        
    old_token: RefreshToken = await refresh_token_model.get_refresh_token_by_id(
        security.decode_refresh_token(refresh_token).token_id,
        conn
    )
    
    if not old_token:
        raise INVALID_REFRESH_TOKEN
    
    if old_token.revoked or old_token.expires_at < datetime.now(timezone.utc):
        if db.pool:
            async with db.pool.acquire() as temp_conn:
                await refresh_token_model.revoke_token_family(old_token.family_id, temp_conn)
        raise INVALID_REFRESH_TOKEN
    
    user: Optional[UserResponse] = await user_model.get_user_by_id(old_token.user_id, conn)
    
    if not user:
        if db.pool:
            async with db.pool.acquire() as temp_conn:
                await refresh_token_model.revoke_token_family(old_token.family_id, temp_conn)
        raise INVALID_REFRESH_TOKEN
    
    access_token_create: AccessTokenCreate = security.create_access_token(
        user.id,
        user.tenant_id
    )
    
    refresh_token_create: RefreshTokenCreate = security.create_refresh_token(user.id, old_token.family_id)
    
    await db_safe_exec(
        refresh_token_model.create_refresh_token(refresh_token_create, conn),
        refresh_token_model.invalidate_token(old_token.id, refresh_token_create.token_id, conn)
    )
    
    security.set_session_token_cookie(
        response,
        access_token_create.jwt_token,
        access_token_create.expires_at,
        refresh_token_create.jwt_token,
        refresh_token_create.expires_at
    )
    
    return user


async def signup(user: UserCreate, rls: RLSConnection) -> UserResponse:
    ctx: UserManagementContext = await user_model.get_user_management_context(
        actor_id=rls.user.user_id,
        proposed_roles=user.roles,
        conn=rls.conn
    )
    
    if not ctx:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    if not ctx.actor_has_management_role:
        raise HTTPException(
            status_code=403, 
            detail=f"Apenas {', '.join(Constants.MANAGEMENT_ROLES)} podem criar novos usuários."
        )
    
    if ctx.actor_privilege_level < ctx.proposed_roles_max_level:
        raise HTTPException(
            status_code=403, 
            detail=f"Você (Nível {ctx.actor_privilege_level}) não pode criar um usuário com nível superior ({ctx.proposed_roles_max_level})."
        )
        
    password_hash = security.hash_password(user.password) if user.password else None
    quick_access_pin_hash = security.hash_password(user.quick_access_pin_hash) if user.quick_access_pin_hash else None
    
    return await db_safe_exec(user_model.create_user(
        user, 
        password_hash, 
        quick_access_pin_hash, 
        rls.user.tenant_id,
        rls.conn
    ))


async def logout(data: DecodedAccessToken, response: Response, conn: Connection) -> None:
    security.unset_session_token_cookie(response)
    await refresh_token_model.revoke_token_by_user_id(
        data.user_id,
        conn
    )
        