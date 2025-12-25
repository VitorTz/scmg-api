from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
        
    identifier: str = Field(
        ..., 
        description="Email ou CPF do usuário"
    )
    password: str = Field(
        ...,
        description="Senha em texto plano"
    )

    @field_validator('identifier')
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        return v.strip()

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return v.strip()