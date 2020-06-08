from typing import Dict, Optional
import aiohttp
from catalyst.service_invoker.types import ParameterInfo, RestfulOperation, SwaggerInfo, OpenAPI

openApi: Optional[OpenAPI] = None
base_url: str = ''

async def read_swagger(url) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, verify_ssl=False) as response:
            assert response.status == 200
            return await response.text()

