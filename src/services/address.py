from fastapi import status
from fastapi.exceptions import HTTPException
from asyncpg import Connection
from typing import Optional
from src.schemas.address import AddressResponse, AddressCreate
from src.model import address as address_model
from src.util import remove_non_digits
from src.db.db import db_safe_exec
import httpx


async def get_cep(cep: str, conn: Connection) -> AddressResponse:
    original_cep = cep
    cep: str = remove_non_digits(cep)
    address: Optional[AddressResponse] = await address_model.get_address(cep, conn)
    
    if address: return address
        
    url = f"https://viacep.com.br/ws/{cep}/json/"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
    except Exception:
        raise HTTPException(detail=f"CEP {original_cep} não encontrado." , status_code=status.HTTP_404_NOT_FOUND)
    
    if resp.status_code != 200:
        raise HTTPException(detail=f"CEP {original_cep} não encontrado." , status_code=status.HTTP_404_NOT_FOUND)
    
    data = resp.json()
    address_create = AddressCreate(
        cep=cep,
        street=data.get("logradouro"),
        complement=data.get("complemento"),
        unit=data.get("unidade"),
        neighborhood=data.get("bairro"),
        city=data.get("localidade"),
        state_code=data.get("uf"),
        state=data.get("estado"),
        region=data.get("regiao"),
        ibge_code=data.get("ibge"),
        gia_code=data.get("gia"),
        area_code=data.get("ddd"),
        siafi_code=data.get("siafi")
    )
    
    return await db_safe_exec(address_model.create_address(address_create, conn))
