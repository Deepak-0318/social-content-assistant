from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ProviderRequest(BaseModel):
    platform: str
    tone: str
    language: str
    media_type: str
    media_summary: str
    user_instructions: str | None = None


class ProviderResponse(BaseModel):
    caption: str = Field(min_length=1, max_length=2200)
    hashtags: list[str] = Field(max_length=30)
    description: str = Field(min_length=1, max_length=2000)


class AIProvider(ABC):
    """Common interface implemented by every AI provider."""

    @abstractmethod
    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        """Generate structured social media content."""
        raise NotImplementedError