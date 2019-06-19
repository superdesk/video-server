import json
import uuid
from datetime import datetime
import tempfile
import logging

import bson
from flask import Response
from flask import current_app as app
from werkzeug.exceptions import BadRequest

from lib.validator import Validator

logger = logging.getLogger(__name__)


def create_file_name(ext):
    """
    Generates a filename using uuid4
    :param ext: file extension
    :return: generated filename
    """

    return "%s.%s" % (uuid.uuid4().hex, ext.lower())


def paginate(cursor, page):
    page_size = app.config.get('ITEMS_PER_PAGE')
    # сalculate number of documents to skip
    skip = page_size * (page - 1)
    # apply skip & limit
    cursor = cursor.skip(skip).limit(page_size)

    return cursor


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


def add_urls(doc):

    def _handle_doc(doc):
        """
        Add url for project's video, timeline thumbnails and preview thumbnail.
        """
        if '_id' in doc:
            doc['url'] = get_url_for_media(doc['_id'], 'video')

            for index, thumb in enumerate(doc['thumbnails']['timeline']):
                thumb['url'] = get_url_for_media(doc.get('_id'), 'thumbnail') + f'?type=timeline&index={index}'

            if doc['thumbnails']['preview']:
                doc['thumbnails']['preview']['url'] = get_url_for_media(doc.get('_id'), 'thumbnail') + '?type=preview'

    if type(doc) is dict:
        _handle_doc(doc)
    elif type(doc) is list:
        docs = doc
        for _doc in docs:
            _handle_doc(_doc)

def save_activity_log(action, project_id, payload=None):
    """
    Inserts an activity record into `activity` collection
    """

    app.mongo.db.activity.insert_one({
        "action": action,
        "project_id": project_id,
        "payload": payload,
        "create_date": datetime.utcnow()
    })


def validate_document(document, schema, **kwargs):
    """
    Validate `document` against provided `schema`
    :param document: document for validation
    :param schema: validation schema
    :param kwargs: additional arguments for `Validator`
    :return: normalized and validated document
    :raise: `BadRequest` if `document` is not valid
    """

    validator = Validator(schema, **kwargs)
    if not validator.validate(document):
        raise BadRequest(validator.errors)
    return validator.document


def get_request_address(request_headers):
    return request_headers.get('HTTP_X_FORWARDED_FOR') or request_headers.get('REMOTE_ADDR')


def create_temp_file(file_stream, file_name):
    """
    Saves `file_stream` into /tmp directory
    :param file_stream: bytes file stream to save
    :param file_name: file name used to save `file_stream`
    :return: file path
    """

    tmp_path = f"{tempfile.gettempdir()}/tmp_video_server_{file_name}"
    try:
        with open(tmp_path, "wb") as f:
            f.write(file_stream)
    except Exception as e:
        logger.error(f'Can not save file stream to tmp directory: {e}')

    return tmp_path
