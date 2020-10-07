import asyncio

import requests
from catalyst.service_invoker.service_interface import invalidate_cache

from catalyst import service_invoker
from catalyst.service_invoker import service_interface
from catalyst.service_invoker.cache import init_cache, init_cache_sync
from catalyst.service_invoker.swagger import get_openAPI_info
import alien

service_invoker.base_url = 'http://api.dev.ostadkar.pro:2390'
response = requests.get('https://api.dev.ostadkar.pro/swaggerui/configs/swagger.yml')
service_invoker.openApi = get_openAPI_info(response.text)

with open('/Volumes/MacHDD/Projects/ostadkar-sale-service/swagger/swagger.yml', 'rt') as f:
    swagger = get_openAPI_info(f.read())


init_cache_sync('redis://localhost/3')

result = service_interface.invoke_inter_service_operation_sync('get_orders_number',
                                                               order_number='gIBf3zZB9P0',
                                                               result_type=alien.OrderDTO,
                                                               swagger=swagger)
print(result.Status)

# loop = asyncio.get_event_loop()
#
#
# async def invoke():
#     await init_cache('redis://localhost/3')
#     result = await service_interface.invoke_inter_service_operation('get_orders_number',
#                                                                     order_number='gIBf3zZB9P0',
#                                                                     result_type=alien.OrderDTO,
#                                                                     swagger=swagger)
#     print(result.Status)
#
#     await invalidate_cache('order', order_number='69hRqRTYRek')
#
#
# loop.run_until_complete(invoke())
