from typing import Any, Literal

from pydantic import BaseModel


class MediaAnalysisResponse(BaseModel):
    upload_id: str
    media_type: Literal["image", "video"]
    processing_status: Literal["completed"] = "completed"
    analysis: dict[str, Any]
    ai_description: str | None = None
    transcript: str | None = None
