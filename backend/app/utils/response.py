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


MAX_PAGE_SIZE = 200


def paginate(query, page: int = 1, page_size: int = 20):
    page = max(page, 1)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = max((total + page_size - 1) // page_size, 1)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
