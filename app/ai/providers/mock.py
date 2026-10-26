from app.ai.providers.base import (
    AIProvider,
    ProviderRequest,
    ProviderResponse,
)


class MockAIProvider(AIProvider):
    """Deterministic provider for development and automated tests."""

    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        context = (
            request.user_instructions.strip()
            if request.user_instructions
            else "a moment worth sharing"
        )

        caption = (
            f"{context.capitalize()} ✨"
            if request.language.lower() in {"english", "en"}
            else f"{context} ✨"
        )

        hashtags = [
            "#SocialContent",
            f"#{request.platform.replace('_', '').replace('-', '')}",
        ]

        description = (
            f"Mock-generated {request.tone} content in "
            f"{request.language} for {request.platform}. "
            f"Media type: {request.media_type}. "
            "This is a test response, not an AI analysis of the media."
        )

        return ProviderResponse(
            caption=caption,
            hashtags=hashtags,
            description=description,
        )