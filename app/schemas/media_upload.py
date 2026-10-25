from typing import Literal

from pydantic import BaseModel, Field


class MediaUploadResponse(BaseModel):
    id: str
    filename: str
    media_type: Literal[
        "image/jpeg",
        "image/png",
        "image/webp",
        "video/mp4",
        "video/quicktime",
    ]
    size_bytes: int = Field(gt=0)
    status: Literal["uploaded"] = "uploaded"
