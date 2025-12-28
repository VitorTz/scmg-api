from pydantic import BaseModel, Field

class NcmResponse(BaseModel):
    
    code: str
    description: str
    federal_national_rate: float
    federal_import_rate: float
    state_rate: float
    municipal_rate: float
    
    class Config:
        from_attributes = True