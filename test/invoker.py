import asyncio
import urllib

import requests

from catalyst import service_invoker
from catalyst.service_invoker import get_swagger_operations
from catalyst.service_invoker import service_interface
from catalyst.service_invoker.swagger import get_swagger_info

service_invoker.base_url = 'http://api.dev.ostadkar.pro:2390'
response = requests.get('https://api.dev.ostadkar.pro/swaggerui/configs/swagger.yml')
with open('/Users/kamyar/Projects/ostadkar-sale-service/swagger/swagger.yml', 'rt') as f:
    service_invoker.operations = get_swagger_operations(f.read())

result =  service_interface.invoke_inter_service_operation_sync('get_orders_number', order_number='12345')

loop = asyncio.get_event_loop()

async def invoke():
    result = await service_interface.invoke_inter_service_operation('get_orders_number', order_number='12345')
    print(result.Status)


loop.run_until_complete(invoke())



