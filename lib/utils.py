import itertools
import uuid

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
    return Response(bson.json_util.dumps(doc), status=status, mimetype='application/json')
