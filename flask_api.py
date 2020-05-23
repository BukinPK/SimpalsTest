from flask import Flask
from flask_restful import Resource, Api, reqparse
import pymongo


app = Flask(__name__)
api = Api(app)

client = pymongo.MongoClient('localhost')
db = client.test


def sub_zero_check(x):
    x = int(x)
    if x <= 0:
        raise Exception('Value of page must be higher than 0')
    return x


class GetAllAds(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('page', default=1, type=sub_zero_check)
    parser.add_argument('page_size', default=30, type=int,
                        choices=range(1, 101))

    def get(self):
        parser = self.parser.parse_args()
        page = parser['page']
        page_size = parser['page_size']

        adverts_count = db.ads.count_documents({})
        ads = db.ads.find(
            projection={'_id': False})[(page-1)*page_size:page*page_size]

        return {'adverts': [ad for ad in ads], 'page_size': page_size,
                'page': page, 'adverts_count': adverts_count}


api.add_resource(GetAllAds, '/')


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
