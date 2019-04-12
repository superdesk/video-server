from celery import Celery
from pymongo import MongoClient
import time

app = Celery('celery_app', broker='pyamqp://guest@localhost//')

METADATA = {
    "filename": "58482c53a121828cc5135de86be5257859ce586281f612d148fa853a75c6f64e",
    "metadata": {
        "length": "69211"
    },
    "contentType": "image/jpeg",
    "md5": "a4abe83c1ad2dccbd996f069765a36ed",
    "chunkSize": 261120,
    "length": 69211,
}


@app.task
def add(doc):
    connection = MongoClient('localhost', 27017)
    video = connection['superdesk']['video']
    doc = METADATA
    ids = video.insert_one(doc.copy())
    time.sleep(5)
    print('instert %s successfully' % ids)
    return True
