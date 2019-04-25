import uuid


def create_file_name(ext):
    return "%s.%s" % (uuid.uuid4().hex, ext)
