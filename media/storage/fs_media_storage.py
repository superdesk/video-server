import logging
import json
import mimetypes
import bson
import gridfs
import os.path
from media import get_collection

logger = logging.getLogger(__name__)
PATH_FS = os.path.dirname(__file__) + '/fs'


def format_id(_id):
    try:
        return bson.ObjectId(_id)
    except bson.errors.InvalidId:
        return _id


class FileSystemMediaStorage():
    def get(self, _id):
        logger.debug('Getting media file with id= %s' % _id)
        _id = format_id(_id)
        try:
            file_name = get_collection('video').find_one({"_id": _id}).get('file_name')
            media_file = (open("%s/%s" % (PATH_FS, file_name), 'r+')).read()
        except Exception:
            media_file = None
        return media_file

    def put(self, content, filename=None, content_type=None, metadata=None, folder=None, **kwargs):
        if '_id' in kwargs:
            kwargs['_id'] = format_id(kwargs['_id'])
        if folder:
            if folder[-1] == '/':
                folder = folder[:-1]
            if filename:
                filename = '{}/{}'.format(folder, filename)
        try:
            logger.info('Adding file {} to the file system'.format(filename))
            open("%s/%s" % (PATH_FS, filename), "w+").write(content)
            get_collection('video').insert_one()
        except Exception as ex:
            logger.info('File filename=%s error ex:' % (filename, ex))

    def delete(self, _id):
        logger.debug('Getting media file with id= %s' % _id)
        _id = format_id(_id)
        try:
            video_collection = get_collection('video')
            file_name = video_collection.find_one({"_id": _id}).get('file_name')
            os.remove("%s/%s" % (PATH_FS, file_name))
            video_collection.remove({'id': _id})
        except Exception:
            media_file = None
        return media_file
