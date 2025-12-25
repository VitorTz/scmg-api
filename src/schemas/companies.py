from pydantic import BaseModel
from typing import Optional


class AddressSchema(BaseModel):
    zip_code: Optional[str]
    street: Optional[str]
    number: Optional[str]
    complement: Optional[str]
    neighborhood: Optional[str]
    city_name: Optional[str]
    city_code: Optional[str]
    state: Optional[str]


class CompanyResponse(BaseModel):
    cnpj: str
    name: Optional[str]
    trade_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    is_simples: bool
    is_mei: bool
    cnae_code: Optional[str]
    cnae_desc: Optional[str]
    address: AddressSchema