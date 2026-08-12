import asyncio

import pytest

from assistant_server.auth import AuthenticationError, RuoYiAuthenticator
from assistant_server.config import Settings


def test_missing_token_is_rejected():
    async def run():
        authenticator = RuoYiAuthenticator(Settings.from_env())
        try:
            with pytest.raises(AuthenticationError):
                await authenticator.authenticate("")
        finally:
            await authenticator.close()

    asyncio.run(run())

