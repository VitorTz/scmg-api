from src.schemas.companies import CompanyResponse
from src.services.nuvem_fiscal import NuvemFiscalAuth
from src.util import remove_non_digits
from fastapi.exceptions import HTTPException
from asyncpg import Connection
from src.model import companies as companies_model
from typing import Optional
import httpx

CACHE_TTL_DAYS = 30


async def get_company(cnpj: str, conn: Connection) -> CompanyResponse:
    clean_cnpj = remove_non_digits(cnpj)
    if len(clean_cnpj) != 14:
        raise HTTPException(status_code=400, detail="CNPJ inválido. Deve conter 14 dígitos.")
        
    company: Optional[CompanyResponse]  = await companies_model.get_company(clean_cnpj, conn)
    if company: return company
    
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

    return await companies_model.create_company(merged_data, data_cnpj, conn)
    