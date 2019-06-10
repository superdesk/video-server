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

    def get_range(self, storage_id, start, length):
        """
        Get a range of stream file
        :param storage_id: storage_id of file
        :param start: start index stream
        :param length: end index stream
        :return:
        """
        try:
            file_path = os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), storage_id)
            file = (open(file_path, 'rb'))
            file.seek(start)
            media_file = file.read(length)
        except Exception as ex:
            logger.error('Cannot get data file %s ex: %s' % (storage_id, ex))
            media_file = None
        return media_file

    def put(self, content, filename, project_id=None, asset_type='project', storage_id=None, content_type=None):
        """
        Put a file into storage.
        Auto create the path, if asset_type is project: <year>/<month>/<day>/<project-id>/<filename>
                        and if asset_type is not project: <year>/<month>/<day>/<project-id>/<asset_type>/<filename>
                        asset_type isnot project, that mean it is sub item contain in project.
        :param content: stream of file, binary type
        :param filename: name of file to save to storage
        :param project_id: project id
        :param asset_type: the folder to store asset under project_id if asset_type is not project
        :param storage_id: storage_id of video
        :param content_type: content type of file
        :return: storage_id
        """
        try:
            if asset_type == 'project':
                # generate storage_id for video
                if not project_id:
                    raise KeyError("asset_type is project, the project_id must be not empty")
                utcnow = datetime.utcnow()
                storage_id = f'{utcnow.year}/{utcnow.month}/{utcnow.day}/{project_id}/{filename}'
            else:
                if not storage_id:
                    raise KeyError("asset_type is not project, must have the storage_id of asset's project")
                storage_id = f'{os.path.dirname(storage_id)}/{asset_type}/{filename}'
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

    def replace(self, content, storage_id, content_type=None):
        """
        replace a file in storage
        :param content: stream file
        :param storage_id: storage_id of file
        :param content_type: content type of file
        :return:
        """
        try:
            # generate storage_id
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
        """
        Delete a file in storage
        :param storage_id: storage_id of file
        :return:
        """
        try:
            file_path = os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), storage_id)
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.info('Deleted media file %s from storage' % storage_id)
            return True
        except Exception as ex:
            logger.error('Cannot delete file %s ex: %s' % (storage_id, ex))
            return False
