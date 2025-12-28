from dotenv import load_dotenv
from uuid import uuid4, UUID
from random import randint
import psycopg
import os


load_dotenv()


import random
import json
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from typing import List, Dict, Any
from faker import Faker

fake = Faker('pt_BR')


def generate_uuid(total: int = 100) -> list[UUID]:
    return [uuid4() for _ in range(total)]


def generate_mock_audit_logs(count: int) -> tuple[tuple[Any]]:
    valid_user_ids = generate_uuid()
    valid_tenant_ids = generate_uuid()

    operations = ['INSERT', 'UPDATE', 'DELETE']
    tables = ['users', 'products', 'orders', 'categories']
    
    data = []

    for _ in range(count):
        operation = random.choice(operations)
        table = random.choice(tables)
        
        # Gera payloads falsos baseados na tabela "imaginária"
        mock_payload = {
            "name": fake.name() if table == 'users' else fake.bs(),
            "status": random.choice(['active', 'pending', 'deleted']),
            "price": round(random.uniform(10.0, 500.0), 2) if table == 'products' else None,
            "updated_by": fake.email()
        }
        
        # Limpa None values para o JSON ficar bonito
        mock_payload = {k: v for k, v in mock_payload.items() if v is not None}

        # Lógica de Valores Antigos/Novos
        old_vals = None
        new_vals = None

        if operation == 'INSERT':
            new_vals = mock_payload
        elif operation == 'DELETE':
            old_vals = mock_payload
        elif operation == 'UPDATE':
            old_vals = mock_payload.copy()
            new_vals = mock_payload.copy()
            new_vals['status'] = 'updated_status_test' # Muda algo para parecer real

        # Gera data aleatória nos últimos 60 dias (para testar partições e filtros)
        random_days = random.randint(0, 60)
        random_seconds = random.randint(0, 86400)
        created_at = datetime.now() - timedelta(days=random_days, seconds=random_seconds)

        row = (
            None,
            "52b1c877-15a5-4bad-b3ca-efe328a30a99",
            operation,
            table,
            uuid4(),
            json.dumps(old_vals) if old_vals else None,
            json.dumps(new_vals) if new_vals else None,
            created_at
        )
        
        data.append(row)

    return tuple(data)


def main() -> None:
    db_url = os.getenv("DATABASE_URL_POSTGRES")
    if not db_url:
        print("Erro: DATABASE_URL não definida.")
        return
    
    params: tuple[tuple[str]] = generate_mock_audit_logs(1000)
    
    with psycopg.connect(db_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM security_audit_log;")
            conn.commit()
            
            cur.executemany(
                """
                    INSERT INTO security_audit_log (
                        user_id,
                        tenant_id,
                        operation,
                        table_name,
                        record_id,
                        old_values,
                        new_values,
                        created_at                   
                    )
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                params
            )
            conn.commit()


if __name__ == "__main__":
    main()