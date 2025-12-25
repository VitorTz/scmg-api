from asyncpg import Connection
from src.schemas.companies import CompanyResponse, AddressSchema
from typing import Optional
import json


CACHE_TTL_DAYS = 30


async def get_company(cnpj: str, conn: Connection) -> Optional[CompanyResponse]:
    row = await conn.fetchrow(
        """
        SELECT 
            * 
        FROM 
            cnpjs
        WHERE 
            cnpj = $1
            AND last_update > (NOW() - make_interval(days => $2))
        """,
        cnpj,
        CACHE_TTL_DAYS
    )
    
    if row:
        return CompanyResponse(
            cnpj=row['cnpj'],
            name=row['name'],
            trade_name=row['trade_name'],
            email=row['email'],
            phone=row['phone'],
            is_simples=row['is_simples'] or False,
            is_mei=row['is_mei'] or False,
            cnae_code=row['cnae_main_code'],
            cnae_desc=row['cnae_main_desc'],
            address=AddressSchema(
                zip_code=row['zip_code'],
                street=row['street'],
                number=row['number'],
                complement=row['complement'],
                neighborhood=row['neighborhood'],
                city_name=row['city_name'],
                city_code=row['city_code'],
                state=row['state']
            )
        )
    
    
async def create_company(data: dict, raw_data: dict, conn: Connection) -> CompanyResponse:
    query = """
        INSERT INTO cnpjs (
            cnpj, 
            name, 
            trade_name,
            is_simples, 
            is_mei, 
            cnae_main_code, 
            cnae_main_desc, 
            zip_code, 
            street, 
            number, 
            complement, 
            neighborhood, 
            city_name, 
            city_code, 
            state,
            email, 
            phone,
            raw_source_cnpj
        ) VALUES (
            $1, 
            $2, 
            $3, 
            $4, 
            $5, 
            $6, 
            $7, 
            $8, 
            $9, 
            $10, 
            $11, 
            $12, 
            $13, 
            $14, 
            $15, 
            $16, 
            $17,
            $18
        )
        ON CONFLICT 
            (cnpj) 
        DO UPDATE SET
            name = EXCLUDED.name,
            is_simples = EXCLUDED.is_simples,
            last_update = CURRENT_TIMESTAMP
    """
    
    await conn.execute(
        query,
        data["cnpj"], 
        data["name"], 
        data["trade_name"],
        data["is_simples"], 
        data["is_mei"],
        data["cnae_code"], 
        data["cnae_desc"],
        data["zip_code"], 
        data["street"], 
        data["number"], 
        data["complement"], 
        data["neighborhood"], 
        data["city_name"], 
        data["city_code"], 
        data["state"],
        data["email"],
        data["phone"],
        json.dumps(raw_data)
    )
    
    return CompanyResponse(
        **data,
        address=AddressSchema(
            zip_code=data["zip_code"],
            street=data["street"],
            number=data["number"],
            complement=data["complement"],
            neighborhood=data["neighborhood"],
            city_name=data["city_name"],
            city_code=data["city_code"],
            state=data["state"]
        )
    )