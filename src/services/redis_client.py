from typing import TypeVar, Type, Callable, Awaitable
from pydantic import BaseModel
from typing import Optional
import redis.asyncio as redis
import os


T = TypeVar("T", bound=BaseModel)


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
        ttl_seconds: int = 3600
    ) -> T:
        redis = cls.get_client()

        # 1. Tenta recuperar do Redis
        try:
            cached_data = await redis.get(key)
            if cached_data:
                return model_class.model_validate_json(cached_data)
        except Exception as e:
            print(f"[CACHE READ ERROR] {e}")

        result = await fetch_function()
        
        try:
            await redis.set(
                key, 
                result.model_dump_json(),
                ex=ttl_seconds
            )
        except Exception as e:
            print(f"[CACHE WRITE ERROR] {e}")

        return result