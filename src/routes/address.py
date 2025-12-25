from fastapi import APIRouter, Depends, status, Path
from fastapi_limiter.depends import RateLimiter
from src.schemas.address import AddressResponse, UserAddressCreate
from src.schemas.rls import RLSConnection
from src.model import address as address_model
from src.security import get_postgres_connection, get_rls_connection
from asyncpg import Connection
from src.services import address as address_service


router = APIRouter(dependencies=[Depends(RateLimiter(times=32, seconds=60))])



@router.get("/{cep}", status_code=status.HTTP_200_OK, response_model=AddressResponse)
async def get_cep(
    cep: str = Path(..., title="CEP", description="CEP do endereço (apenas números)"),
    conn: Connection = Depends(get_postgres_connection)
):
    return await address_service.get_cep(cep, conn)


@router.post("/users", status_code=status.HTTP_204_NO_CONTENT)
async def register_user_address(
    address: UserAddressCreate, 
    rls: RLSConnection = Depends(get_rls_connection)
):
    await address_model.create_user_address(address, rls.conn)