from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseEntity(BaseModel):
    id: int | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)
