import uuid
import bson


def create_file_name(ext):
    return "%s.%s" % (uuid.uuid4().hex, ext)


def format_id(_id):
    try:
        return bson.ObjectId(_id)
    except bson.errors.InvalidId:
        return _id
