import uuid
from cerberus import Validator


def create_file_name(ext):
    return "%s.%s" % (uuid.uuid4().hex, ext)


def validate_json(schema, doc):
    v = Validator(schema)
    return v.validate(doc)
