from typing import Any
from pydantic import BaseModel


class APIResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None

    @classmethod
    def success(cls, data: Any = None, message: str = "success") -> "APIResponse":
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, message: str = "error", code: int = 400) -> "APIResponse":
        return cls(code=code, message=message, data=None)


class PaginatedData(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
