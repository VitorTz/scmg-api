from pydantic import BaseModel
from asyncpg import Connection, Record
from src.schemas.user import UserResponse
from typing import Optional
 


class RLSConnection(BaseModel):
    
    user: Record
    conn: Connection


class AdminConnectionWithUser(BaseModel):
    
    user: Optional[UserResponse]
    conn: Connection