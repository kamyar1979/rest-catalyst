import asyncio


import requests

from catalyst import service_invoker
from catalyst.service_invoker import service_interface
from catalyst.service_invoker.cache import init_cache, init_cache_sync
from catalyst.service_invoker.swagger import get_openAPI_info
import alien

service_invoker.base_url = 'http://api.dev.ostadkar.pro:2390'
response = requests.get('https://api.dev.ostadkar.pro/swaggerui/configs/swagger.yml')
with open('/Users/kamyar/Projects/ostadkar-sale-service/swagger/swagger.yml', 'rt') as f:
    service_invoker.openApi = get_openAPI_info(f.read())

init_cache_sync('redis://localhost', 3)

result =  service_interface.invoke_inter_service_operation_sync('get_orders_number', order_number='69hRqRTYRek', result_type=alien.OrderDTO)

loop = asyncio.get_event_loop()

async def invoke():
    await init_cache('redis://localhost', 3)
    result = await service_interface.invoke_inter_service_operation('get_orders_number', order_number='69hRqRTYRek', result_type=alien.OrderDTO)
    print(result.Status)


loop.run_until_complete(invoke())



