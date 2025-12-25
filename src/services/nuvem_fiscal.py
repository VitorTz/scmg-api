from datetime import datetime, timedelta, timezone
from asyncpg import Connection
import httpx
import os


class NuvemFiscalAuth:
    
    SERVICE_NAME = "nuvem_fiscal"

    @classmethod
    async def get_token(cls, conn: Connection) -> str:
        row = await conn.fetchrow(
            """
            SELECT 
                access_token 
            FROM 
                app_tokens 
            WHERE 
                service_name = $1
                AND expires_at > (NOW() + interval '5 minutes')
            """,
            NuvemFiscalAuth.SERVICE_NAME
        )

        if row: return row['access_token']

        print(f"[NUVEM FISCAL] [PID {os.getpid()}] 🔄 Token expirado ou inexistente. Renovando na API...")
        return await cls._fetch_and_save_new_token(conn)

    @classmethod
    async def _fetch_and_save_new_token(cls, conn: Connection) -> str:
        client_id = os.getenv("NUVEM_CLIENT_ID")
        client_secret = os.getenv("NUVEM_CLIENT_SECRET")
        url_auth = "https://auth.nuvemfiscal.com.br/oauth/token"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "empresa cnpj nfe"
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url_auth, data=payload)
            resp.raise_for_status()
            
            data = resp.json()
            token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
                        
            expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=expires_in)
            
            await conn.execute(
                """
                INSERT INTO app_tokens (
                    service_name, 
                    access_token, 
                    expires_at, 
                    updated_at
                )
                VALUES 
                    ($1, $2, $3, CURRENT_TIMESTAMP)
                ON CONFLICT 
                    (service_name) 
                DO UPDATE SET 
                    access_token = EXCLUDED.access_token,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = EXCLUDED.updated_at;
                """,
                NuvemFiscalAuth.SERVICE_NAME,
                token,
                expires_at
            )
            
            return token