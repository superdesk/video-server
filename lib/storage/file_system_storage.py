import logging
import os
from datetime import datetime

from flask import current_app as app


from .interface import MediaStorageInterface

logger = logging.getLogger(__name__)


class FileSystemStorage(MediaStorageInterface):

    def get(self, storage_id):
        """
        Get stream file
        :param storage_id: full file path
        :return:
        """
        try:
            file_path = os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), storage_id)
            media_file = (open(file_path, 'rb')).read()
        except Exception as ex:
            logger.error('Cannot get data file %s ex: %s' % (storage_id, ex))
            media_file = None
        return media_file

    def get_range(self, storage_id, start, end):
        """
        Get a range of stream file
        :param file_path: full file path
        :param start: start index stream
        :param end: end index stream
        :return:
        """
        try:
            file_path = os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), storage_id)
            file = (open(file_path, 'rb'))
            file.seek(start)
            media_file = file.read(end - start + 1)
        except Exception as ex:
            logger.error('Cannot get data file %s ex: %s' % (storage_id, ex))
            media_file = None
        return media_file

    def put(self, content, filename, content_type=None):
        """
        Put a file into storage
        :param content: stream of file, binary type
        :param filename: full file path
        :param content_type: content type of file
        :return: storage_id
        """
        file_path = ''
        try:
            # generate storage_id
            utcnow = datetime.utcnow()
            storage_id = f'{utcnow.year}/{utcnow.month}/{utcnow.day}/{filename}'
            file_path = os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), storage_id)
            # check if dir exists, if not create it
            file_dir = os.path.dirname(file_path)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            # write stream to file
            with open(file_path, "wb") as f:
                f.write(content)
            logger.info('Put media file %s to storage' % storage_id)
            return storage_id
        except Exception as ex:
            logger.error('Cannot put file %s ex: %s' % (storage_id, ex))
            return None

    def url_for_media(self, project_id):
        """
        Get url project for reviewing
        :param project_id:
        :return:
        """
        return f'{app.config.get("VIDEO_MEDIA_PREFIX")}/{str(project_id)}'

    def replace(self, content, storage_id, content_type=None):
        file_path = ''
        try:
            # generate storage_id
            utcnow = datetime.utcnow()
            file_path = os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), storage_id)
            # check if dir exists, if not create it
            file_dir = os.path.dirname(file_path)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            # write stream to file
            with open(file_path, "wb") as f:
                f.write(content)
            logger.info('Replace media file %s in storage' % storage_id)
            return storage_id
        except Exception as ex:
            logger.error('Cannot replace file %s ex: %s' % (storage_id, ex))
            return None

    def delete(self, storage_id):
        try:
            file_path = os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), storage_id)
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.info('Deleted media file %s from storage' % storage_id)
            return True
        except Exception as ex:
            logger.error('Cannot delete file %s ex: %s' % (storage_id, ex))
            return False
