import itertools
import json
import uuid
from datetime import datetime

import bson
from flask import Response


def create_file_name(ext):
    return "%s.%s" % (uuid.uuid4().hex, ext)


def format_id(_id):
    try:
        return bson.ObjectId(_id)
    except bson.errors.InvalidId:
        return _id


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


def represents_int(s):
    try:
        return int(s)
    except ValueError:
        return None
