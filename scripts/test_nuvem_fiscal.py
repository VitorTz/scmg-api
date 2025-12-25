import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente (.env)
load_dotenv()


async def get_auth_token() -> str:
    """
    Autentica na Nuvem Fiscal usando OAuth2 (Client Credentials)
    e retorna o 'access_token' válido.
    """
    client_id = os.getenv("NUVEM_CLIENT_ID")
    client_secret = os.getenv("NUVEM_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("❌ Erro: CLIENT_ID ou CLIENT_SECRET não configurados no .env")
        return None

    url_auth = "https://auth.nuvemfiscal.com.br/oauth/token"
    
    # Payload exigido pelo fluxo Client Credentials
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "empresa cnpj nfe" # O escopo necessário para consultar CNPJ
    }
    
    print("🔑 Gerando novo token de acesso...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Note que é um POST enviando FORM-DATA (data=...), não json.
            resp = await client.post(url_auth, data=payload)
            
            if resp.status_code != 200:
                print(f"❌ Falha na Autenticação: {resp.status_code} - {resp.text}")
                return None
            
            token_data = resp.json()
            print(token_data)
            return token_data.get("access_token")
            
        except Exception as e:
            print(f"❌ Erro de conexão na autenticação: {e}")
            return None


async def test_cnpj_integration(cnpj_input: str):
    clean_cnpj = ''.join(filter(str.isdigit, cnpj_input))
    print(f"🔍 CNPJ Sanitizado: {clean_cnpj}")

    if len(clean_cnpj) != 14:
        print(f"❌ Erro: CNPJ inválido. Tamanho: {len(clean_cnpj)}")
        return

    # 2. [NOVO] Obtém o Token dinamicamente
    token = await get_auth_token()
    
    if not token:
        print("❌ Abortando: Não foi possível autenticar.")
        return

    # O Token gerado é usado aqui 👇
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🚀 Iniciando requisição paralela à Nuvem Fiscal...")

    # 3. Consulta à API (Mesma lógica da rota)
    async with httpx.AsyncClient() as client:                
        task_empresas = client.get(f"https://api.nuvemfiscal.com.br/empresas/{clean_cnpj}", headers=headers)
        task_cnpj = client.get(f"https://api.nuvemfiscal.com.br/cnpj/{clean_cnpj}", headers=headers)
        
        # Dispara juntas
        resp_empresas, resp_cnpj = await asyncio.gather(task_empresas, task_cnpj)
    
    # Validações básicas
    if resp_cnpj.status_code == 404:
        print("❌ Erro: CNPJ não encontrado na base Federal (404).")
        return

    print(f"✅ Status Endpoint /empresas (Estadual): {resp_empresas.status_code}")
    print(f"✅ Status Endpoint /cnpj (Federal): {resp_cnpj.status_code}")
    
    # Extração de JSON
    data_empresas = resp_empresas.json() if resp_empresas.status_code == 200 else {}
    data_cnpj = resp_cnpj.json() if resp_cnpj.status_code == 200 else {}
    
    # 4. Lógica de Merge (Cópia exata da sua rota)
    addr_source = data_cnpj.get("endereco", {})
    city_info = addr_source.get("municipio", {})
    
    simples = data_cnpj.get("simples", {})
    simei = data_cnpj.get("simei", {})
    atividade = data_cnpj.get("atividade_principal", {})

    merged_data = {
        "cnpj": clean_cnpj,
        "name": data_cnpj.get("razao_social") or data_empresas.get("nome_razao_social"),
        "trade_name": data_cnpj.get("nome_fantasia") or data_empresas.get("nome_fantasia"),        
        
        # IE é o dado mais crítico aqui
        "ie": data_empresas.get("inscricao_estadual"), 
        "im": data_empresas.get("inscricao_municipal"),
        
        "email": data_cnpj.get("email") or data_empresas.get("email"),        
        "phone": (
            f"{data_cnpj['telefones'][0]['ddd']}{data_cnpj['telefones'][0]['numero']}" 
            if data_cnpj.get("telefones") and len(data_cnpj["telefones"]) > 0 else data_empresas.get("fone")
        ),        
        "is_simples": simples.get("optante", False),
        "is_mei": simei.get("optante", False),
        "cnae_code": atividade.get("codigo"),
        "cnae_desc": atividade.get("descricao"),
        
        # Endereço
        "zip_code": addr_source.get("cep") or data_empresas.get("endereco", {}).get("cep"),
        "street": addr_source.get("logradouro") or data_empresas.get("endereco", {}).get("logradouro"),
        "number": addr_source.get("numero") or data_empresas.get("endereco", {}).get("numero"),
        "complement": addr_source.get("complemento") or data_empresas.get("endereco", {}).get("complemento"),
        "neighborhood": addr_source.get("bairro") or data_empresas.get("endereco", {}).get("bairro"),
        "city_name": city_info.get("descricao") or data_empresas.get("endereco", {}).get("cidade"),
        "city_code": city_info.get("codigo_ibge"),
        "state": addr_source.get("uf") or data_empresas.get("endereco", {}).get("uf"),
    }
    
    # [REMOVIDO] Insert no Banco de Dados
    # await conn.execute(query...)
    
    # 5. Exibição do Resultado Final
    print("\n" + "="*40)
    print("RESULTADO PROCESSADO (O que iria para o DB/Return)")
    print("="*40)
    print(json.dumps(merged_data, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    CNPJ_TESTE = "83017350000198"
    asyncio.run(test_cnpj_integration(CNPJ_TESTE))