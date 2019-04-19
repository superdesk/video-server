from pymongo import MongoClient
from flask import current_app as app
from cerberus import Validator


def get_collection(colection, db=None):
    db = app.config.get('MONGO_DBNAME') if not db else db
    connection = MongoClient(app.config.get('MONGO_HOST'), app.config.get('MONGO_PORT'))
    return connection[db][colection]


def blueprint(blueprint, app, **kwargs):
    """Register flask blueprint.
    :param blueprint: blueprint instance
    :param app: flask app instance
    """
    blueprint.kwargs = kwargs
    prefix = None
    app.register_blueprint(blueprint, url_prefix=prefix, **kwargs)


def validate_json(schema, doc):
    v = Validator(schema)
    return v.validate(doc)
