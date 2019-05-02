import os
import logging
from flask import current_app as app

from .interface import MediaStorageInterface

logger = logging.getLogger(__name__)


class FileSystemStorage(MediaStorageInterface):

    def get(self, file_path):
        """
        Get stream file
        :param doc:
        :return:
        """
        try:
            media_file = (open(file_path, 'rb')).read()
        except Exception as ex:
            logger.error('Cannot get data file %s ex: %s' % (file_path, ex))
            media_file = None
        return media_file

    def put(self, content, file_path):
        """
        Put a file into storage
        :param content: stream of file, binary type
        :param file_path:  file_name and folder contain file
        :return:
        """
        try:
            # Check dir contain file is exist, if not create
            file_dir = os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), os.path.dirname(file_path))
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            # write stream to file
            with open(os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), file_path), "wb") as f:
                f.write(content)
            logger.info('Put media file %s to storage' % file_path)
            return True
        except Exception as ex:
            logger.error('Cannot put file %s ex: %s' % (file_path, ex))
            return False

    def replace(self, file_path):
        pass

    def delete(self, file_path):
        try:
            if os.path.exists(os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), file_path)):
                os.remove(file_path)
            logger.info('Deleted media file %s from storage' % file_path)
            return True
        except Exception as ex:
            logger.error('Cannot delete file %s ex: %s' % (file_path, ex))
            return False
