from pymongo import MongoClient
from flask import current_app as app


def get_collection(colection, db=None):
    db = app.config.get('MONGO_DBNAME') if not db else db
    connection = MongoClient(app.config.get('MONGO_URI'), app.config.get('MONGO_PORT'))
    return connection[db][colection]
