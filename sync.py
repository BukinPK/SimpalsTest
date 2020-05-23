import asyncio
import sys
from datetime import datetime
from time import sleep
import math
import requests
import pymongo
import aiohttp
from lxml import html


# Проект маленький, поэтому ArgumentParser не использую
TOKEN = sys.argv[1]

client = pymongo.MongoClient('localhost')
db = client.test

# Не вижу особого смысла в использовании асинхрона в данной задаче,
# так как лимиты всё равно не позволяют увеличить скорость скачивания.
# Но в задаче был асинхрон, поэтому я его использовал.

# Семафор на скачивание страниц
sem1 = asyncio.Semaphore(5)
# Семафор на скачивание объявлений.
# Больше одного -- упираемся в лимиты, ловим ошибки
# 2-3 потока -- лучшая скорость, но ошибок больше, что может привести к бану.
sem2 = asyncio.Semaphore(2)
# максимальный размер страницы с объявлениями
PAGE_SIZE = 100
# Курс, используемый, в случае если сайт BNM не доступен.
# После восстановления доступа, заменяется актуальным.
course = 20
# Оптимальная задержка для одного потока.
sleep_time = .1
# Период между синхронизациями
PERIOD = 60


class Api:
    endpoint = 'https://partners-api.999.md/'

    def __init__(self, token, lang='ru', timeout=1):
        self.token = token
        self.lang = lang
        self.timeout = timeout

    def get(self, method: str, params=None):
        payload = {'lang': self.lang}
        if params is not None:
            payload.update(params)
        return requests.get(self.endpoint + method, params=payload,
                            auth=(self.token, ''), timeout=self.timeout).json()

    async def get_async(self, method: str, params=None):
        payload = {'lang': self.lang}
        if params is not None:
            payload.update(params)
        async with aiohttp.ClientSession() as session:
            async with session.get(self.endpoint + method, params=payload,
                                   auth=aiohttp.BasicAuth(self.token, ''),
                                   timeout=self.timeout) as r:
                return await r.json()


async def get_page(adverts, page=1):
    async with sem1:
        while True:
            try:
                data = await api.get_async(
                    'adverts', {'page': page, 'page_size': PAGE_SIZE})
                await asyncio.sleep(sleep_time)
                break
            except Exception as ex:
                print(f'Error on page {page} -- '
                      f'[{ex.__class__.__name__}: {ex}]')
                await asyncio.sleep(sleep_time)
        adverts.extend(data['adverts'])
        print(f'Page {page} is downloaded successful')


async def get_and_save_ad(ad_id):
    async with sem2:
        while True:
            try:
                datetime_start = datetime.now()
                data = await api.get_async(f'adverts/{ad_id}')
                delta = datetime.now() - datetime_start
                await asyncio.sleep(sleep_time)
                break
            except Exception as ex:
                print(f'Error on download ad with id {ad_id}, sleep for '
                      f'{sleep_time} -- [{ex.__class__.__name__}: {ex}]')
                await asyncio.sleep(sleep_time)
        # Я делаю реплейсы, чтобы не возникло ситуации, когда пользователь
        # хочет получить доступ к моему API, в то время как коллекция уже
        # дропнута, но не обновлена новыми данными. Это дольше, потому что
        # приходится вносить данные поочерёдно, но безопаснее.
        data = convert_currency(data)
        db.ads.find_one_and_replace({'id': data['id']}, data, upsert=True)
        print(f'Ad with id {ad_id} '
              f'is downloaded successful with time: {delta}')


def convert_currency(data):
    try:
        if data['price']['unit'] == 'eur':
            data['price']['unit'] = 'mdl'
            data['price']['value'] = data['price']['value'] * course
    finally:
        return data


def get_course():
    r = requests.get('https://bnm.md', timeout=10)
    if r.status_code == 200:
        return html.fromstring(r.text).xpath(
            '//span[@class="currency" and @title="Euro"]/../span[2]/text()')[0]


def main():
    global course
    # Запрашиваю первую страницу, чтобы узнать сколько страниц необходимо
    # скачать асинхронно
    while True:
        try:
            response = api.get('adverts', {'page_size': PAGE_SIZE})
            break
        except Exception as ex:
            print(f'Error on page 1 -- [{ex.__class__.__name__}: {ex}]')
            sleep(sleep_time)
    print(f'Page 1 is downloaded successful')

    adverts = response['adverts']
    page_count = math.ceil(response['subtotal'] / PAGE_SIZE)

    # Скачивание всех страниц с объявлениями, из которых нам нужны только id
    tasks = [asyncio.ensure_future(get_page(adverts, page))
             for page in range(2, page_count + 1)]
    loop.run_until_complete(asyncio.wait(tasks))

    # Если сайт BNM недоступен, то используется последный курс,
    # который получилось спарсить.
    course = get_course() or course

    # Так как метод "adverts", используемый для получения списка объявлений
    # не предоставляет каких-либо индикаторов изменения изменения объявления,
    # приходится скачивать все объявления, если мы хотим синхронизировать
    # изменения объявлений, а не только их создание и удаление.
    id_to_update = [ad['id'] for ad in adverts]
    if id_to_update:
        tasks = [asyncio.ensure_future(get_and_save_ad(ad_id))
                 for ad_id in id_to_update]
        loop.run_until_complete(asyncio.wait(tasks))

    # Удаление отсутствующих в текущем запросе объявлений из базы
    db.ads.delete_many({'id': {'$not': {'$in': id_to_update}}})


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    api = Api(TOKEN)

    while True:
        try:
            main()
        except Exception as ex:
            print(f'Main loop exception -- [{ex.__class__.__name__}: {ex}]')
            sleep(PERIOD)
        print(f'Sleep for period of {PERIOD} seconds.')
        sleep(PERIOD)
