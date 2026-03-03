from pydantic import BaseModel, Field


class DummyJsonImportRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=500)
    skip: int = Field(default=0, ge=0)
    update_existing: bool = False
    default_category_name: str = Field(default="Imported")


class JsonProductImportRequest(BaseModel):
    products: list[dict] = Field(default_factory=list)
    update_existing: bool = False
    default_category_name: str = Field(default="Imported")


class ProductImportResult(BaseModel):
    source: str
    total_input: int
    created_products: int
    updated_products: int
    skipped_products: int
    created_categories: int
    errors: list[str] = Field(default_factory=list)
