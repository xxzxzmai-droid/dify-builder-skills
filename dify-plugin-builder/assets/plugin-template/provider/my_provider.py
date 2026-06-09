from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class MyProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        # 无凭证工具直接通过;需要 API key 时在这里校验。
        try:
            return
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))
