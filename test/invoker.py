import asyncio
import urllib

import requests

from catalyst import service_invoker
from catalyst.service_invoker import get_swagger_operations
from catalyst.service_invoker import service_interface

service_invoker.base_url = 'https://api.dev.ostadkar.pro'
response = requests.get('https://api.dev.ostadkar.pro/swaggerui/swagger.yml')
service_invoker.operations = get_swagger_operations(response.text)

result =  service_interface.invoke_inter_service_operation_sync('get_orders_number', order_number='12345')

loop = asyncio.get_event_loop()

async def invoke():
    result = await service_interface.invoke_inter_service_operation('get_orders_number', order_number='12345')
    print(result.Status)


loop.run_until_complete(invoke())

