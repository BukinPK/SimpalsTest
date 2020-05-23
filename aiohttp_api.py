import json
from aiohttp import web
import pymongo


client = pymongo.MongoClient('localhost')
db = client.test
app = web.Application()


async def get_all_ads(request):
    try:
        page = int(request.query.get('page') or 1)
        page_size = int(request.query.get('page_size') or 30)
        if page <= 0:
            raise Exception('page value be higher than 0')
        if page_size <= 0 or page_size > 100:
            raise Exception('page_size value must be higher than 0'
                            ' and lower or equal than 100')
    except Exception as ex:
        text = {'message': str(ex)}
        code = 500
    else:
        adverts_count = db.ads.count_documents({})
        ads = db.ads.find(
            projection={'_id': False})[(page-1)*page_size:page*page_size]

        text = {'adverts': [ad for ad in ads], 'page_size': page_size,
                'page': page, 'adverts_count': adverts_count}
        code = 200

    return web.Response(text=json.dumps(text, indent=4),
                        content_type='application/json', status=code)


app.add_routes([web.get('/', get_all_ads)])

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=5001)
