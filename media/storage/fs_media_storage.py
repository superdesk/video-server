import logging
import bson
import os
from media import get_media_collection

logger = logging.getLogger(__name__)
PATH_FS = os.path.dirname(__file__) + '/fs'


def format_id(_id):
    try:
        return bson.ObjectId(_id)
    except bson.errors.InvalidId:
        return _id


class MediaStorage(object):
    def get(self, id):
        pass

    def put(self, content, filename, version=1, client_info=None, parent=None, metadata=None, folder=None, **kwargs):
        pass

    def edit(self, content, filename, version=1, client_info=None, parent=None, metadata=None, folder=None, **kwargs):
        pass

    def delete(self):
        pass


class FileSystemMediaStorage(MediaStorage):
    def get(self, _id):
        """
        Get a stream file in storage
        :param _id:
        :return:
        """
        logger.info('Getting media file with id= %s' % _id)
        _id = format_id(_id)
        try:
            file_name = get_media_collection().find_one({"_id": _id}).get('filename')
            media_file = (open("%s/%s" % (PATH_FS, file_name), 'r+')).read()
        except Exception:
            media_file = None
        return media_file

    def put(self, content, filename, version=1, client_info=None, parent=None, metadata=None, processing=False,
            **kwargs):
        """
        Put a file into storage
        Create record for this file

        :param content:
        :param filename:
        :param version:
        :param client_info:
        :param parent:
        :param metadata:
        :param processing:
        :param kwargs:
        :return:
        """
        logger.info('put media file with file name = %s to storage' % filename)
        try:
            if not os.path.exists(PATH_FS):
                os.makedirs(PATH_FS)
            #: write stream file to storage
            with open("%s/%s" % (PATH_FS, filename), "wb") as f:
                f.write(content)
            #: create a record in storage
            doc = {
                'filename': filename,
                'metadata': metadata,
                'client_info': client_info,
                'version': version,
                'processing': processing,
                "parent": parent,
                'thumbnails': {}
            }
            for k, v in kwargs.items():
                doc[k] = v
            get_media_collection().insert_one(doc)
            return doc
        except Exception as ex:
            logger.info('File filename=%s error ex:' % (filename, ex))

    def edit(self, content, filename, version=1, client_info=None, parent=None, metadata=None, folder=None, **kwargs):
        pass

    def delete(self, _id):
        logger.debug('delete media file with id= %s' % _id)
        _id = format_id(_id)
        try:
            media_collection = get_media_collection()
            file_name = media_collection.find_one({"_id": _id}).get('file_name')
            os.remove("%s/%s" % (PATH_FS, file_name))
            media_collection.remove({'id': _id})
        except Exception:
            media_file = None
        return media_file
