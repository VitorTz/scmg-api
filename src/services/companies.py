from src.schemas.companies import CompanyResponse, AddressSchema
from src.services.nuvem_fiscal import NuvemFiscalAuth
from src.util import remove_non_digits
from fastapi.exceptions import HTTPException
from asyncpg import Connection
import httpx
import json

CACHE_TTL_DAYS = 30


async def get_company(cnpj: str, conn: Connection) -> CompanyResponse:
    clean_cnpj = remove_non_digits(cnpj)
    if len(clean_cnpj) != 14:
        raise HTTPException(status_code=400, detail="CNPJ inválido. Deve conter 14 dígitos.")
        
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
        clean_cnpj,
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
    
    try:
        token: str = await NuvemFiscalAuth.get_token(conn) 
    except Exception as e:
        print(f"[NUVEM FISCAL] [ERROR] Auth: {e}")
        raise HTTPException(status_code=502, detail="Falha na autenticação externa")

    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:                
        resp_cnpj = await client.get(f"https://api.nuvemfiscal.com.br/cnpj/{clean_cnpj}", headers=headers)
    
    if resp_cnpj.status_code == 404:
        raise HTTPException(status_code=404, detail="CNPJ não encontrado na base Federal.")
    
    data_cnpj = resp_cnpj.json() if resp_cnpj.status_code == 200 else {}
    
    addr_source = data_cnpj.get("endereco", {})
    city_info = addr_source.get("municipio", {})
    
    # Dados Tributários (Do endpoint /cnpj)
    simples = data_cnpj.get("simples", {})
    simei = data_cnpj.get("simei", {})
    atividade = data_cnpj.get("atividade_principal", {})

    # Objeto final
    merged_data = {
        "cnpj": clean_cnpj,
        "name": data_cnpj.get("razao_social"),
        "trade_name": data_cnpj.get("nome_fantasia"),
        "email": data_cnpj.get("email"), 
        "phone": (
            f"{data_cnpj['telefones'][0]['ddd']}{data_cnpj['telefones'][0]['numero']}"
        ),        
        "is_simples": simples.get("optante", False),
        "is_mei": simei.get("optante", False),
        "cnae_code": atividade.get("codigo"),
        "cnae_desc": atividade.get("descricao"),
        "zip_code": addr_source.get("cep"),
        "street": addr_source.get("logradouro"),
        "number": addr_source.get("numero"),
        "complement": addr_source.get("complemento"),
        "neighborhood": addr_source.get("bairro"),
        "city_name": city_info.get("descricao"),
        "city_code": city_info.get("codigo_ibge"),
        "state": addr_source.get("uf")
    }
    
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
        merged_data["cnpj"], 
        merged_data["name"], 
        merged_data["trade_name"],
        merged_data["is_simples"], 
        merged_data["is_mei"],
        merged_data["cnae_code"], 
        merged_data["cnae_desc"],
        merged_data["zip_code"], 
        merged_data["street"], 
        merged_data["number"], 
        merged_data["complement"], 
        merged_data["neighborhood"], 
        merged_data["city_name"], 
        merged_data["city_code"], 
        merged_data["state"],
        merged_data["email"],
        merged_data["phone"],
        json.dumps(data_cnpj)
    )
    
    return CompanyResponse(
        **merged_data,
        address=AddressSchema(
            zip_code=merged_data["zip_code"],
            street=merged_data["street"],
            number=merged_data["number"],
            complement=merged_data["complement"],
            neighborhood=merged_data["neighborhood"],
            city_name=merged_data["city_name"],
            city_code=merged_data["city_code"],
            state=merged_data["state"]
        )
    )