import abc


class MediaStorageInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, storage_id):
        """
        Read and return a file based on `storage_id`
        :param storage_id: unique starage id
        :type storage_id: str
        :return: file
        :rtype: bytes
        """
        pass

    @abc.abstractmethod
    def put(self, content, filename, project_id, asset_type, storage_id=None, content_type=None):
        """
        Save file into a storage.
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
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
    def delete(self, storage_id):
        """
        Delete a file from the storage
        :param storage_id: starage id of file to remove
        :type storage_id: str
        """
        pass

    @abc.abstractmethod
    def delete_dir(self, storage_id):
        """
        Delete an entire directory where `storage_id` is located
        :param storage_id: unique storage
        :type storage_id: str
        """
        # NOTE: meaning `directory` might be different for different storage backends
        pass
