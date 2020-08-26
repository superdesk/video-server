import json
import uuid
from datetime import datetime
from tempfile import mkstemp
import logging

import bson
from flask import Response, make_response
from flask import current_app as app
from flask import url_for
from werkzeug.exceptions import BadRequest

from .validator import Validator

logger = logging.getLogger(__name__)


def create_file_name(ext):
    """
    Generates a filename using uuid4
    :param ext: file extension
    :type ext: str
    :return: generated filename
    :rtype: str
    """

    return "%s.%s" % (uuid.uuid4().hex, ext.lower())


def paginate(cursor, page):
    """
    Apply pagination for mongo cursor
    :param cursor: mongo cursor with projects list
    :type cursor: pymongo.cursor.Cursor
    :param page: page to apply
    :type page: int
    :return: mongo cursor with projects list with skiped items according to page number
    :rtype: pymongo.cursor.Cursor
    """

    page_size = app.config.get('ITEMS_PER_PAGE')
    # сalculate number of documents to skip
    skip = page_size * (page - 1)
    # apply skip & limit
    cursor = cursor.skip(skip).limit(page_size)

    return cursor


def json_response(doc=None, status=200):
    """
    Serialize document fetched from mongo and return flask response with applicaton/json mimetype.
    :param doc: document fetched from mongo
    :type doc: dict
    :param status: http respponse status
    :type status: int
    :return: flask http response
    :rtype: flask.wrappers.Response
    """

    class JSONEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, bson.ObjectId):
                return str(o)
            if isinstance(o, datetime):
                return o.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            return json.JSONEncoder.default(self, o)

    return Response(JSONEncoder().encode(doc), status=status, mimetype='application/json')


def add_urls(doc):
    """
    Add urls for project's media
    :param doc: project or list of projects
    :type doc: dict or list
    """

    def _handle_doc(doc):
        PROXY_ENABLED = app.config.get('FILE_STREAM_PROXY_ENABLED')
        PROXY_URL = app.config.get('FILE_STREAM_PROXY_URL')

        def _url_for(*args, **kwargs):
            kwargs['_external'] = not PROXY_ENABLED
            url = url_for(*args, **kwargs)

            if PROXY_ENABLED:
                url = PROXY_URL + url

            return url

        if '_id' in doc:
            url = _url_for(
                'projects.get_raw_video',
                project_id=doc['_id']
            )

            doc['url'] = url

            for index, thumb in enumerate(doc['thumbnails']['timeline']):
                thumb['url'] = _url_for(
                    'projects.get_raw_timeline_thumbnail',
                    project_id=doc['_id'],
                    index=index
                )

            if doc['thumbnails']['preview'] or doc['processing']['thumbnail_preview']:
                doc['thumbnails']['preview']['url'] = _url_for(
                    'projects.get_raw_preview_thumbnail',
                    project_id=doc['_id']
                )

    if type(doc) is dict:
        _handle_doc(doc)
    elif type(doc) is list:
        docs = doc
        for _doc in docs:
            _handle_doc(_doc)


def save_activity_log(action, project_id, payload=None):
    """
    Inserts an activity record into `activity` collection
    :param action: action
    :type action: str
    :param project_id: project related to log record
    :type project_id: bson.objectid.ObjectId
    :param payload: additional log information
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
    :type document: dict
    :param schema: validation schema
    :type schema: dict
    :param kwargs: additional arguments for `Validator`
    :return: normalized and validated document
    :rtype: dict
    :raise: `BadRequest` if `document` is not valid
    """

    validator = VideoValidator(schema, **kwargs)
    if not validator.validate(document):
        raise BadRequest(validator.errors)
    return validator.document


class VideoValidator(Validator):
    def _normalize_coerce_crop_to_dict(self, value):
        """Convert crop string (x,y,w,h) to dict
        """
        # cerberus run coercion func before validation rule
        # if provided value is malformed, return original value (str) to validate against regex rule
        try:
            x, y, width, height = [int(item) for item in value.split(',')]
            return {"x": x, "y": y, "width": width, "height": height}
        except ValueError:
            return value
        except (TypeError, AttributeError):
            self._error('crop', 'must be of string type')
            return value

    def _is_malformed_format(self, value):
        return type(value) != dict

    def _validate_allow_crop_width(self, limit, field, value):
        """Test allowed crop width range
        The rule's arguments are validated against this schema:
        {'min': 'limit[0]', 'max': 'limit[1]'}
        """
        if self._is_malformed_format(value):
            return
        if limit and len(limit) == 2:
            wmin, wmax = limit
            width = value.get('width', 0)
            if width < wmin:
                self._error(field, f"width {width} is less than minimum allowed crop width ({wmin})")
            if width > wmax:
                self._error(field, f"width {width} is greater than maximum allowed crop width ({wmax})")

    def _validate_allow_crop_height(self, limit, field, value):
        """Test allowed crop height range
        The rule's arguments are validated against this schema:
        {'min': 'limit[0]', 'max': 'limit[1]'}
        """
        if self._is_malformed_format(value):
            return
        if limit and len(limit) == 2:
            hmin, hmax = limit
            height = value.get('height', 0)
            if height < hmin:
                self._error(field, f"height {height} is less than minimum allowed crop height ({hmin})")
            if height > hmax:
                self._error(field, f"height {height} is greater than maximum allowed crop height ({hmax})")

    def _normalize_coerce_trim_to_dict(self, value):
        """Convert trim string (x,y) to dict
        """
        try:
            start, end = [float(item) for item in value.split(',')]
            return {"start": start, "end": end}
        except ValueError:
            return value
        except (TypeError, AttributeError):
            self._error('trim', 'must be of string type')
            return value

    def _validate_min_trim_start(self, min_trim, field, value):
        """Test minimum allowed trim start value
        The rule's arguments are validated against this schema:
        {'min': 'min_trim'}
        """
        if self._is_malformed_format(value):
            return
        if min_trim is not None and value.get('start', -1) < min_trim:
            self._error(field, "start time must be greater than %s" % min_trim)

    def _validate_min_trim_end(self, min_trim, field, value):
        """Test minium allowed trim end value
        The rule's arguments are validated against this schema:
        {'min': 'min_trim'}
        """
        if self._is_malformed_format(value):
            return
        if min_trim is not None and value.get('end', -1) < min_trim:
            self._error(field, "end time must be greater than %s" % min_trim)


def get_request_address(request_headers):
    return request_headers.get('HTTP_X_FORWARDED_FOR') or request_headers.get('REMOTE_ADDR')


def create_temp_file(file_stream, suffix=None):
    """
    Saves `file_stream` into /tmp directory
    :param file_stream: file to save
    :type file_stream: bytes
    :param suffix: the file name will end with that suffix, otherwise there will be no suffix.
    :type suffix: str
    :return: file path
    :rtype: str
    """

    fd, path = mkstemp(suffix=suffix)

    with open(fd, "wb") as f:
        f.write(file_stream)

    return path


def storage2response(storage_id, headers=None, status=200, start=None, length=None):
    """
    Fetch binary using `storage_id` and return http response.

    :param storage_id: Unique storage id
    :type storage_id: str
    :param headers: header for response
    :type headers: dict
    :param status: http status code
    :type status: int
    :param start: start file's position to read
    :type start: int
    :param length: the number of bytes to be read from the file
    :type length: int
    :return: response
    :rtype: flask.wrappers.Response
    """

    if not headers:
        headers = {}

    if start is not None:
        bytes = app.fs.get_range(storage_id, start, length)
    else:
        bytes = app.fs.get(storage_id)

    resp = make_response(bytes)
    resp.headers = headers
    return resp, status
