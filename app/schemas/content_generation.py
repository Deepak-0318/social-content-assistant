from typing import Literal

from pydantic import BaseModel, Field


Platform = Literal[
    "instagram",
    "facebook",
    "youtube",
    "threads",
    "linkedin",
]

Tone = Literal[
    "funny",
    "professional",
    "emotional",
    "aesthetic",
    "educational",
    "viral-style",
]


class ContentGenerationRequest(BaseModel):
    upload_id: str = Field(min_length=1, max_length=36)
    platform: Platform
    tone: Tone = "aesthetic"
    language: str = Field(default="English", min_length=2, max_length=50)
    user_instructions: str | None = Field(
        default=None,
        max_length=1000,
    )


class GeneratedContent(BaseModel):
    caption: str
    hashtags: list[str]
    description: str


class ContentGenerationResponse(BaseModel):
    upload_id: str
    platform: Platform
    tone: Tone
    language: str
    provider: str
    content: GeneratedContent