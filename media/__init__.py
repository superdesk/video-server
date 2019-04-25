from pymongo import MongoClient
from flask import current_app as app


def get_collection(colection, db=None):
    db = app.config.get('MONGO_DBNAME') if not db else db
    connection = MongoClient(app.config.get('MONGO_HOST'), app.config.get('MONGO_PORT'))
    return connection[db][colection]


def get_media_collection():
    return get_collection('video')


def get_thumbnails_collection():
    return get_collection('video_thumbnails')


def blueprint(blueprint, app, **kwargs):
    """Register flask blueprint.
    :param blueprint: blueprint instance
    :param app: flask app instance
    """
    blueprint.kwargs = kwargs
    prefix = None
    app.register_blueprint(blueprint, url_prefix=prefix, **kwargs)
