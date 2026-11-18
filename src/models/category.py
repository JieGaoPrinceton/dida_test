from pydantic import BaseModel


class CategoryBase(BaseModel):
    name: str
    parent_id: int | None = None
    description: str | None = None
    keywords: list[str] | None = None
    level: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int
    children: list["CategoryResponse"] = []

    model_config = {"from_attributes": True}
