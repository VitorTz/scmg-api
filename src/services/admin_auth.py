from fastapi import Header, status
from fastapi.exceptions import HTTPException
from typing import Optional
import secrets
import os


class AdminAPIKeyAuth:    
    
    def __init__(self):
        self.api_keys: str[str] = self._load_api_keys()
    
    def _load_api_keys(self) -> set[str]:
        """Carrega API keys de variáveis de ambiente"""
        keys_env = os.getenv("ADMIN_API_KEYS", "")
        
        if not keys_env:
            temp_key = secrets.token_urlsafe(32)
            print(f"⚠️  WARNING: No API keys configured!")
            print(f"🔑 Using temporary API key: {temp_key}")
            print(f"💡 Set ADMIN_API_KEYS environment variable in production")
            return {temp_key}
        
        return set(key.strip() for key in keys_env.split(",") if key.strip())
    
    async def verify_api_key(
        self, 
        x_api_key: Optional[str] = Header(None, description="API Key de administrador")
    ) -> bool:        
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key não fornecida. Use o header 'X-API-Key'",
                headers={"WWW-Authenticate": "ApiKey"}
            )
                
        if not any(secrets.compare_digest(x_api_key, valid_key) for valid_key in self.api_keys):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API Key inválida"
            )
        return True