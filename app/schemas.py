from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# ── Auth ──────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None


# ── Books ─────────────────────────────────────────────────────────────────────


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    isbn: str = Field(..., pattern=r"^\d{10}(\d{3})?$")
    price: float = Field(..., gt=0)
    genre: str | None = Field(None, max_length=50)
    published_year: int | None = Field(None, ge=1000, le=2100)
    in_stock: bool = True

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, v: str) -> str:
        digits = v.replace("-", "")
        if len(digits) not in (10, 13):
            raise ValueError("ISBN must be 10 or 13 digits")
        return digits


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    author: str | None = Field(None, min_length=1, max_length=100)
    price: float | None = Field(None, gt=0)
    genre: str | None = Field(None, max_length=50)
    published_year: int | None = Field(None, ge=1000, le=2100)
    in_stock: bool | None = None


class BookResponse(BookBase):
    id: int
    owner_id: int | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class BookListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[BookResponse]


# ── Health ────────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
