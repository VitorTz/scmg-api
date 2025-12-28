from typing import TypeVar, Type, Callable, Awaitable
from pydantic import BaseModel
from typing import Optional
import asyncio
import redis.asyncio as redis
import os


T = TypeVar("T", bound=BaseModel)


async def set_cache_background(redis_client: redis.Redis, key: str, value: Type[T], ttl: int):
    try:
        payload = value.model_dump_json()
        await redis_client.set(key, payload, ex=ttl)
    except Exception as e:
        print(f"[ERROR] Falha ao salvar cache em background para {key}: {e}")
            
            
class RedisService:
    
    _client: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        if cls._client is None:
            cls._connect()
        return cls._client

    @classmethod
    def _connect(cls):
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("A variável de ambiente REDIS_URL não está configurada.")
        
        cls._client = redis.from_url(
            redis_url, 
            decode_responses=True,
            encoding="utf-8",            
        )

    @classmethod
    async def check_connection(cls):
        client = cls.get_client()
        try:
            await client.ping()
            print("[REDIS] [CONEXÃO ESTABELECIDA COM SUCESSO!]")
        except Exception as e:
            print(f"[REDIS] [ERROR] [{e}]")            
            raise e

    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.close()
            print("[REDIS] [CONEXÃO FECHADA]")
            cls._client = None
            
    @classmethod
    async def get_or_set_cache(
        cls,
        key: str,
        model_class: Type[T],
        fetch_function: Callable[[], Awaitable[T]],
        ttl: int = 3600
    ) -> T:
        redis_client = cls.get_client()
                
        try:
            cached_data = await redis_client.get(key)
            if cached_data:
                return model_class.model_validate_json(cached_data)
        except Exception as e:
            print(f"[CACHE READ ERROR] {e}")

        result = await fetch_function()
        
        asyncio.create_task(set_cache_background(redis_client, key, result, ttl))

        return result
    