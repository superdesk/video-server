import itertools
import json
import uuid
from datetime import datetime

import bson
from flask import Response
from flask import current_app as app
from werkzeug.exceptions import BadRequest

from lib.validator import Validator


def create_file_name(ext):
    """
    Generates a filename using uuid4
    :param ext: file extension
    :return: generated filename
    """

    return "%s.%s" % (uuid.uuid4().hex, ext)


def paginate(iterable, page_size):
    while True:
        i1, i2 = itertools.tee(iterable)
        iterable, page = (itertools.islice(i1, page_size, None),
                          list(itertools.islice(i2, page_size)))
        if len(page) == 0:
            break
        yield page


def json_response(doc=None, status=200):
    """
    Serialize mongodb documents and return Response with applicaton/json mimetype
    """

    class JSONEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, bson.ObjectId):
                return str(o)
            if isinstance(o, datetime):
                return o.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            return json.JSONEncoder.default(self, o)

    return Response(JSONEncoder().encode(doc), status=status, mimetype='application/json')


def get_url_for_media(project_id, media_type):
    """
    Get url project for reviewing media
    :param project_id: id of project
    :return:
    """

    if media_type == 'video':
        suffix = app.config.get('VIDEO_URL_SUFFIX')
    elif media_type == 'thumbnail':
        suffix = app.config.get('THUMBNAIL_URL_SUFFIX')
    else:
        raise KeyError('Invalid media_type')

    return '/'.join(x.strip('/') for x in (app.config.get('VIDEO_SERVER_URL'), str(project_id), suffix))


def save_activity_log(action, project_id, storage_id, payload=None):
    """
    Inserts an activity record into `activity` collection
    """

    app.mongo.db.activity.insert_one({
        "action": action,
        "project_id": project_id,
        "storage_id": storage_id,
        "payload": payload,
        "create_date": datetime.utcnow()
    })


def check_request_schema_validity(request_schema, schema, **kwargs):
    validator = Validator(schema, **kwargs)
    if not validator.validate(request_schema):
        raise BadRequest(validator.errors)
    return validator.document


def get_request_address(request_headers):
    return request_headers.get('HTTP_X_FORWARDED_FOR') or request_headers.get('REMOTE_ADDR')
