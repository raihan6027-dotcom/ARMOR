from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class RegisterResponse(BaseModel):
    user_id: str
    email: EmailStr
    message: str = "User registered successfully"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class MeResponse(BaseModel):
    user_id: str
    email: EmailStr
