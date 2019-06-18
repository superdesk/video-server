import abc


class MediaStorageInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, storage_id):
        pass

    @abc.abstractmethod
    def put(self, content, filename, project_id, asset_type, storage_id=None, content_type=None):
        pass

    @abc.abstractmethod
    def replace(self, content, storage_id, content_type=None):
        pass

    @abc.abstractmethod
    def get_range(self, storage_id, start, length):
        pass

    @abc.abstractmethod
    def delete(self, storage_id):
        pass

    @abc.abstractmethod
    def delete_dir(self, storage_id):
        pass
