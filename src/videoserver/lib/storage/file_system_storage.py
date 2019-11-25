import os
import shutil
import logging
from datetime import datetime

from flask import current_app as app

from .interface import MediaStorageInterface

logger = logging.getLogger(__name__)


class FileSystemStorage(MediaStorageInterface):
    """
    File system storage.
    Use file system to store files.
    """

    @staticmethod
    def _get_file_path(storage_id):
        """
        Build and return full file path based on `storage_id`.
        :param storage_id: unique starage id
        :type storage_id: str
        :return: file path
        :rtype: str
        """

        return os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'), storage_id)

    def get(self, storage_id):
        """
        Read and return a file based on `storage_id`
        :param storage_id: unique starage id
        :type storage_id: str
        :return: file
        :rtype: bytes
        """

        try:
            with open(self._get_file_path(storage_id), 'rb') as rb:
                media_file = rb.read()
        except Exception as e:
            logger.error(f'FileSystemStorage:get:{storage_id}: {e}')
            raise e

        return media_file

    def get_range(self, storage_id, start, length):
        """
        Read and return a file's chunks based on `storage_id`
        :param storage_id: unique starage id
        :type storage_id: str
        :param start: start file's position to read
        :param length: the number of bytes to be read from the file
        :return: file
        :rtype: bytes
        """

        try:
            with open(self._get_file_path(storage_id), 'rb') as rb:
                rb.seek(start)
                media_file = rb.read(length)
        except Exception as e:
            logger.error(f'FileSystemStorage:get_range:{storage_id}: {e}')
            raise e

        return media_file

    def put(self, content, filename, project_id=None, asset_type='project', storage_id=None, content_type=None,
            override=True):
        """
        Save file into a fs storage.

        Use <year>/<month>/<day>/<project-id>/<filename> path if `asset_type` is 'project', `project_id` is required.
        Use <year>/<month>/<day>/<project-id>/<asset_type>/<filename> if `asset_type` is not 'project', `storage_id`
        is required.

        Example:
         - video file: 2019/6/11/5cff82a6fe985e1e3bddb326/3ada91761c6048bdb3dd42a2463d5df8.mp4
         - thumbnail:  2019/6/11/5cff82a6fe985e1e3bddb326/thumbnails/3ada91761c6048bdb3dd42a2463d5df8_timeline_00.png

        :param content: file to save
        :type content: bytes
        :param filename: name which will be used when store a file
        :type filename: str
        :param project_id: unique project id
        :type project_id: bson.objectid.ObjectId
        :param asset_type: asset type
        :type asset_type: str
        :param storage_id: unique starage id of file
        :type storage_id: str
        :param content_type: content type of file
        :type content_type: str
        :return: storage id of just saved file
        :rtype: str
        """

        if asset_type == 'project':
            if not project_id:
                raise ValueError("Argument 'project_id' is required when 'asset_type' is 'project'")
            # generate storage_id for project
            utcnow = datetime.utcnow()
            storage_id = f'{utcnow.year}/{utcnow.month}/{utcnow.day}/{project_id}/{filename}'
        else:
            if not storage_id:
                raise ValueError("Argument 'storage_id' is required when 'asset_type' is not 'project'")
            # generate storage_id
            storage_id = f'{os.path.dirname(storage_id)}/{asset_type}/{filename}'

        file_path = self._get_file_path(storage_id)
        # check if file exists
        if os.path.exists(file_path):
            if not override:
                raise Exception(f'File {file_path} already exists, use "replace" method instead.')
            self.replace(content, storage_id)

        # check if dir exists, if not create it
        file_dir = os.path.dirname(file_path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        # write stream to file
        try:
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.error(f'FileSystemStorage:put:{storage_id}: {e}')
            raise e

        logger.info(f"Saved file '{storage_id}' to fs storage")
        return storage_id

    def replace(self, content, storage_id, content_type=None):
        """
        Replace a file in the storage
        :param content: file to replace with
        :type content: bytes
        :param storage_id: starage id of file for replacement
        :type storage_id: str
        :param content_type: content type of file
        :type content_type: str
        """

        file_path = self._get_file_path(storage_id)
        # check if dir exists, if not create it
        file_dir = os.path.dirname(file_path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        # write stream to file
        try:
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.error(f'FileSystemStorage:replace:{storage_id}: {e}')
            raise e
        else:
            logger.info(f'Replaced file "{storage_id}" in fs storage')

    def delete(self, storage_id):
        """
        Delete a file from the storage
        :param storage_id: starage id of file to remove
        :type storage_id: str
        """

        file_path = self._get_file_path(storage_id)

        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Removed '{file_path}' from fs storage")
        else:
            logger.warning(f"File '{file_path}' was not found in fs storage.")

    def delete_dir(self, storage_id):
        """
        Delete an entire folder where `storage_id` is located
        :param storage_id: unique storage
        :type storage_id: str
        """

        dir_path = os.path.dirname(self._get_file_path(storage_id))

        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path)
            logger.info(f"Removed '{dir_path}' from fs storage")
        else:
            logger.warning(f"Directory '{dir_path}' was not found in fs storage.")
