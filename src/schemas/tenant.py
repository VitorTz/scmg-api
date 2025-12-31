from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class TenantPublicInfo(BaseModel):
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    slug: str
    created_at: datetime
    