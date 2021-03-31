# TestWork
Все зависимости в `Pipfile`
## Синхронизация
USAGE: `pipenv run python sync.py <TOKEN>`

При запуске, как скрипта, выкачивает все объявления и добавляет (либо заменяет)
их в базу в бесконечном цикле. По окончании каждой итерации удаляет из 
базы объявления, которые отсутствуют в списке скачанных объявлений.
## API
USAGE: 

`pipenv run python flask_api.py`

`pipenv run python aiohttp_api.py`

Сделал две реализации API.
Одна на `aiohttp`, другая с использованием модуля `flask-restfull`
## ElasticSearch
Для синхронизации с ElasticSearch использовал `mongo-connector`
Тут код писать не пришлось.

Запуск осуществляется командой:

`pipenv run mongo-connector -m localhost:27017 -t localhost:9200 -d elastic2_doc_manager  --auto-commit-interval=0`

Либо от рута, если модуль установлен глобально.

Перед запуском необходимо сделать реплику на mongodb.
Это можно сделать, выставив `replSet=ReplName` в конфиге mongodb, 
либо добавить ключ `--replSet ReplName` в сервисном файле демона.

Затем сделать `rs.initiate()` в консоли mongodb.

Далее следует оформить `mongo-connector` в качестве демона.
Для этого, на гитхабе проекта, есть скрипт генерации сервисного файла.
