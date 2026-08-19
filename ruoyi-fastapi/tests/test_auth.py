import asyncio

import pytest

from assistant_server.core.config import Settings
from assistant_server.services.authentication import AuthenticationError, RuoYiAuthenticator


def test_missing_token_is_rejected():
    async def run():
        authenticator = RuoYiAuthenticator(Settings.from_env())
        try:
            with pytest.raises(AuthenticationError):
                await authenticator.authenticate("")
        finally:
            await authenticator.close()

    asyncio.run(run())
