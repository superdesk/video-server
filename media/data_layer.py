from pymongo import MongoClient
from flask import current_app as app


def get_collection(name):
    connection = MongoClient(app.config['MONGO_URI'], app.config['MONGO_PORT'])
    return connection[app.config['MONGO_DBNAME']][name]
