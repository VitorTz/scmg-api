from datetime import date
from dotenv import load_dotenv
import psycopg
import os
import csv

load_dotenv()


VERSION = "25.2.H"
SOURCE = "IBPT/empresometro.com.br"
DATA_INICIO = date(2025, 11, 20)
DATA_FIM = date(2026, 1, 31)
FILE = "/mnt/HD/54717619000140/TabelaIBPTaxSC25.2.H.csv"


def stream_csv_ibpt_as_tuple():
    try:
        with open(FILE, mode='r', encoding='latin1') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                try:
                    yield (
                        row['codigo'].replace('.', ''),          # code
                        row['descricao'][:255],                  # description (safe truncate)
                        float(row['nacionalfederal'].replace(',', '.')), # federal_national
                        float(row['importadosfederal'].replace(',', '.')), # federal_import
                        float(row['estadual'].replace(',', '.')),        # state
                        float(row['municipal'].replace(',', '.'))        # municipal
                    )
                except ValueError:
                    print(f"Erro ao converter linha no arquivo {FILE}: {row.get('codigo')}")
                    continue
    except FileNotFoundError as e:
        print(f"ERRO CRÍTICO: Arquivo não encontrado: {FILE}")
        raise e

def main() -> None:
    db_url = os.getenv("DATABASE_URL_POSTGRES")
    if not db_url:
        print("Erro: DATABASE_URL não definida.")
        return
    
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            
            print(f"Inserindo versão {VERSION}...")
            
            cur.execute(
                """
                INSERT INTO ibpt_versions (
                    version, 
                    valid_from, 
                    valid_until, 
                    source
                )
                VALUES 
                    (%s, %s, %s, %s)
                ON CONFLICT 
                    (version)
                DO UPDATE SET
                    valid_from = EXCLUDED.valid_from,
                    valid_until = EXCLUDED.valid_until;
                """,
                (VERSION, DATA_INICIO, DATA_FIM, SOURCE)
            )
                        
            print(f"Processando...")                
            iterador_dados = stream_csv_ibpt_as_tuple()
            cur.executemany(
                """
                INSERT INTO fiscal_ncms (
                    code,
                    description,
                    federal_national_rate, 
                    federal_import_rate,
                    state_rate, 
                    municipal_rate
                )
                VALUES 
                    (%s, %s, %s, %s, %s, %s)
                ON CONFLICT 
                    (code)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    federal_national_rate = EXCLUDED.federal_national_rate,
                    federal_import_rate = EXCLUDED.federal_import_rate,
                    state_rate = EXCLUDED.state_rate,
                    municipal_rate = EXCLUDED.municipal_rate
                """,
                iterador_dados
            )
            print(f"Processamento concluido.")
            
            conn.commit()
            print("Sucesso! Todos os dados foram commitados.")

if __name__ == "__main__":
    main()