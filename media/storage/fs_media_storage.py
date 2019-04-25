import logging
import os
from datetime import datetime

import bson

from media import get_media_collection, get_thumbnails_collection

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

    def get_record(self, _id):
        pass

    def get_file(self, doc):
        pass

    def put(self, content, filename, metadata, mime_type, type='video', **kwargs):
        pass

    def edit(self, content, filename, metadata, mime_type, type='video', **kwargs):
        pass

    def delete(self):
        pass


class FileSystemMediaStorage(MediaStorage):
    def get(self, _id):
        """
        Get record in database and stream file in storage
        :param _id:
        :return:
        """
        logger.info('Getting media file with id= %s' % _id)
        _id = format_id(_id)
        file_stream = None
        doc = self.get_record(_id)
        if doc:
            file_stream = self.get_file(doc)
        return doc, file_stream

    def get_record(self, _id):
        """
        Only get record in database and list record thumbnails in video.
        :param _id:
        :return:
        """
        doc = get_media_collection().find_one({"_id": _id})
        if doc:
            #: get data for thumbnails
            thumbnails = doc.get('thumbnails')
            if thumbnails:
                ids = list(thumbnails.values())[0]
                number = list(thumbnails.keys())[0]
                timeline_thumbnails = []
                for id in ids:
                    timeline_thumbnails.append(get_thumbnails_collection().find_one({'_id': id}))
                doc['thumbnails'] = {number: timeline_thumbnails}
        else:
            doc = get_thumbnails_collection().find_one({"_id": _id})
        return doc

    def get_file(self, doc):
        """
            only get stream file
        :param doc:
        :return:
        """
        filename = doc.get('filename')
        dir_file = doc.get('folder')
        try:
            media_file = (open("%s/%s/%s" % (PATH_FS, dir_file, filename), 'r+')).read()
        except Exception as ex:
            logger.error('Can not get data filename=%s error ex: %s' % (filename, ex))
            media_file = None
        return doc, media_file

    def put(self, content, filename, metadata, mime_type, type='video', **kwargs):
        """
        Put a file into storage
        Create record for this file
        :param content:
        :param filename:
        :param metadata:
        :param mime_type:
        :param type:
        :param kwargs:
        :return:
        """
        logger.info('Put media file with file name = %s to storage' % filename)
        try:
            createtime = datetime.utcnow()
            year = createtime.year
            month = createtime.month
            #: write stream file to storage
            dir_file = "%s/%s/%s" % (PATH_FS, year, month)
            if not os.path.exists(dir_file):
                os.makedirs(dir_file)
            with open("%s/%s" % (dir_file, filename), "wb") as f:
                f.write(content)
            #: create a record in storage
            doc = {
                'filename': filename,
                'folder': "%s/%s" % (year, month),
                'metadata': metadata,
                'create_time': createtime,
                'mime_type': mime_type
            }
            for k, v in kwargs.items():
                doc[k] = v

            if type == "thumbnail":
                get_media_collection().insert_one(doc)
            else:
                get_thumbnails_collection().insert_one(doc)

            return doc
        except Exception as ex:
            logger.error('File filename=%s error ex: %s' % (filename, ex))

    def edit(self, content, filename, version=1, client_info=None, parent=None, metadata=None, folder=None, **kwargs):
        pass

    def delete(self, _id):
        logger.debug('delete media file with id= %s' % _id)
        _id = format_id(_id)
        try:
            media_collection = get_media_collection()
            doc = media_collection.find_one({"_id": _id})
            filename = doc.get('file_name')
            dir_file = doc.get('folder')
            os.remove(open("%s/%s/%s" % (PATH_FS, dir_file, filename)))
            media_collection.remove({'id': _id})
        except Exception as ex:
            logger.error('Cannot delete filename=%s error ex: %s' % (filename, ex))
            return False
        return True
