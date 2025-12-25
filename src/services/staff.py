from src.schemas.user import UserResponse
from src.schemas.staff import UserRoleUpdate
from src.exceptions import DatabaseError
from src.model import staff as staff_model
from typing import Optional
from asyncpg import Connection


async def update_user_roles(data: UserRoleUpdate, conn: Connection):
    user: Optional[UserResponse] = await staff_model.update_user_roles(data.user_id, data.roles, conn)
    
    if user is None:
        return DatabaseError(
            detail="Usuário não encontrado", 
            code=404, 
            log_msg=f"Não foi possível atualizar as funções do usuário {data}"
        )
        
    return user