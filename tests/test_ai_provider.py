import asyncio

from app.ai.providers.base import ProviderRequest, ProviderResponse
from app.ai.providers.mock import MockAIProvider


def test_mock_provider_returns_structured_content():
    async def run_test():
        provider = MockAIProvider()

        request = ProviderRequest(
            platform="instagram",
            tone="aesthetic",
            language="English",
            media_type="image",
            media_summary="JPEG image, 1024x1280",
            user_instructions="A peaceful evening",
        )

        result = await provider.generate(request)

        assert isinstance(result, ProviderResponse)
        assert result.caption
        assert result.hashtags
        assert result.description
        assert "instagram" in result.description

    asyncio.run(run_test())