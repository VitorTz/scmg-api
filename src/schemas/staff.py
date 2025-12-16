from pydantic import BaseModel, Field
from typing import List
from uuid import UUID


class UserRoleUpdate(BaseModel):
    
    roles: List[str] = Field(
        ...,
        description="Papeis que o usuário acumula no sistema"
    )
    
    user_id: UUID