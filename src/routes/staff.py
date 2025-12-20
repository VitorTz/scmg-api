from fastapi import APIRouter, Depends, status
from src.schemas.user import UserResponse, UserCreate
from src.schemas.rls import RLSConnection
from src.schemas.staff import UserRoleUpdate
from src.security import get_rls_connection
from src.model import user as user_model
from src.controller import auth


router = APIRouter()


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse    
)
async def register_user(user: UserCreate, rls: RLSConnection = Depends(get_rls_connection)):
    return await auth.signup(user, rls)


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse
)
async def update_roles(data: UserRoleUpdate, rls: RLSConnection = Depends(get_rls_connection)):
    await rls.conn.execute(
        """
        WITH deleted AS (
            DELETE FROM 
                user_roles
            WHERE 
                user_id = $1
        )
        INSERT INTO user_roles (
            id, 
            role
        )
        SELECT 
            $1, 
            unnest($2::text[])
        ON CONFLICT 
            (id, role) 
        DO NOTHING
        """,
        data.user_id,
        data.roles 
    )
    return user_model.get_user_by_id(data.user_id, rls.conn)