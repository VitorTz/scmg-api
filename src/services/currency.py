from src.schemas.currency import Currency, CurrencyCreate
from asyncpg import Connection
from src.model import currency as currency_model
from src.constants import Constants
from src.util import minutes_since
from fastapi import status
from fastapi.exceptions import HTTPException
from typing import Optional
import httpx


async def get_currencies(conn: Connection):
    currency: Optional[Currency] = await currency_model.get_last_currency_data(conn)
    if not currency or minutes_since(currency.created_at) >= Constants.CURRENCY_UPDATE_TIME_IN_MINUTES:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(Constants.EXCHANGE_RATE_URL)
                resp.raise_for_status()
        except Exception as e:
            print(f"[CURRENCY] [CLIENT ERROR] {e}")
            raise HTTPException(
                    detail="Não foi possível encontrar dados sobre a cotação.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        try:
            data = resp.json()
            if not data.get("success", False):
                if currency: return currency
                raise HTTPException(
                    detail="Não foi possível encontrar dados sobre a cotação.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            quotes = data['quotes']
            currency = CurrencyCreate(
                usd=1 / quotes["BRLUSD"],
                ars=1 / quotes["BRLARS"],
                eur=1 / quotes["BRLEUR"],
                uyu=1 / quotes["BRLUYU"],
                clp=1 / quotes["BRLCLP"],
                pyg=1 / quotes["BRLPYG"]
            )
            return await currency_model.create_currency_data(currency, conn)
        except Exception as e:
            raise e

    return currency
