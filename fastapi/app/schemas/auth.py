from pydantic import BaseModel, Field, model_validator


class LoginRequest(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=255)
    username: str | None = Field(default=None, min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_identity(self) -> "LoginRequest":
        if self.email or self.username:
            return self
        raise ValueError("Either email or username is required")

    @property
    def identity(self) -> str:
        return (self.email or self.username or "").strip()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
