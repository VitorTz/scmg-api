from asyncpg import Connection
from src.schemas.user import UserResponse
from src.schemas.token import DecodedAccessToken
from typing import Optional
 


class RLSConnection:
    
    def __init__(self, user: DecodedAccessToken, conn: Connection):
        self.user = user
        self.conn = conn


class AdminConnectionWithUser:
    
    def __init__(self, user: Optional[UserResponse], conn: Connection):
        self.user = user
        self.conn = conn
    