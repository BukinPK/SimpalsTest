from time import sleep
import math
import requests
import pymongo
import aiohttp

import settings


PAGE_SIZE = 100  # максимальный размер страницы с объявлениями
UPDATE_PERIOD = 60  # Период между синхронизациями
DOWNLOAD_DELAY = 1  # Задержка между запросами к API

client = pymongo.MongoClient(settings.MONGO_SERVER)
db = client[settings.MONGO_DB_NAME]


class Api:
    endpoint = settings.ENDPOINT

    def __init__(self, token, lang='ru', timeout=1):
        self.token = token
        self.lang = lang
        self.timeout = timeout

    def get(self, method: str, params: dict = None):
        payload = {'lang': self.lang}
        if params is not None:
            payload.update(params)
        return requests.get(self.endpoint + method, params=payload,
                            auth=(self.token, ''), timeout=self.timeout).json()

    async def get_async(self, method: str, params: dict = None):
        payload = {'lang': self.lang}
        if params is not None:
            payload.update(params)
        async with aiohttp.ClientSession() as session:
            async with session.get(self.endpoint + method, params=payload,
                                   auth=aiohttp.BasicAuth(self.token, ''),
                                   timeout=self.timeout) as r:
                return await r.json()


def main():
    # Запрашиваю первую страницу, чтобы узнать сколько страниц необходимо скачать
    res = api.get('adverts', {'page_size': PAGE_SIZE})
    print(f'Page 1 is downloaded successful')

    adverts = res['adverts']
    page_count = math.ceil(res['subtotal'] / PAGE_SIZE)

    # Скачивание всех страниц с объявлениями, из которых нам нужны только id
    for page in range(2, page_count+1):
        sleep(DOWNLOAD_DELAY)
        res = api.get('adverts', {'page': page, 'page_size': PAGE_SIZE})
        adverts.extend(res['adverts'])
        print(f'Page {page} is downloaded successful')

    # Так как метод "adverts", используемый для получения списка объявлений
    # не предоставляет каких-либо индикаторов изменения изменения объявления,
    # приходится скачивать все объявления, если мы хотим синхронизировать
    # изменения объявлений, а не только их создание и удаление.
    id_to_update = [ad['id'] for ad in adverts]
    for ad_id in id_to_update:
        sleep(DOWNLOAD_DELAY)
        data = api.get(f'adverts/{ad_id}')
        print(f'Ad {ad_id} downloaded')
        if data['price']['unit'] == 'eur':
            mdl = {c['unit']: c for c in data['price']['currencies']}.get('mdl')
            data['price'].update(mdl)
        db.ads.find_one_and_replace({'id': data['id']}, data, upsert=True)

    # Удаление отсутствующих в текущем запросе объявлений из базы
    db.ads.delete_many({'id': {'$not': {'$in': id_to_update}}})


if __name__ == '__main__':
    api = Api(settings.TOKEN, timeout=5)

    while True:
        try:
            main()
        except Exception as ex:
            print(f'{ex.__class__.__name__}: {ex}')
        print(f'Sleep {UPDATE_PERIOD}')
        sleep(UPDATE_PERIOD)
