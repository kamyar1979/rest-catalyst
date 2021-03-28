import asyncio

import requests
from catalyst.service_invoker.service_interface import invalidate_cache

from catalyst import service_invoker, init_i18n
from catalyst.service_invoker import service_interface
from catalyst.service_invoker.cache import init_cache, init_cache_sync
from catalyst.service_invoker.swagger import get_openAPI_info
import alien

service_invoker.base_url = 'http://api.dev.ostadkr.com:6666'
response = requests.get('https://inventory.dev.ostadkr.com/swagger/ostadkar-services/ostadkar_swagger.yml')
service_invoker.openApi = get_openAPI_info(response.text)

# response2 = requests.get('https://inventory.dev.ostadkr.com/swagger/chista.yml', 'rt')
# swagger = get_openAPI_info(response2.text)


init_cache_sync('redis://localhost/3')

# result = service_interface.invoke_inter_service_operation_sync('get_orders_number',
#                                                                order_number='gIBf3zZB9P0',
#                                                                result_type=alien.OrderDTO,
#                                                                swagger=swagger)


# result = service_interface.invoke_inter_service_operation_sync('search_location',
#                                                                search_phrase='یوسف آباد',
#                                                                swagger=swagger,
#                                                                security={'APIKey': '6m5RM4p5kfApFTo72bEUlwsr6O0G6Vnl'})
# print(result.Status)
# print(result.Body)
loop = asyncio.get_event_loop()

async def invoke():
    await init_cache('redis://localhost/3')
    result = await service_interface.invoke_inter_service_operation('city_slug_services_details_get',
                                                                    city_slug='tehran',
                                                                    service_slug='carpentry',
                                                                    result_type=alien.CityServiceDTO)

    print(result.Status)
    print(result.Body)

    await invalidate_cache('order', order_number='iK7ueu5jBnu')


loop.run_until_complete(invoke())
