import abc


class MediaStorageInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, file_path):
        pass

    @abc.abstractmethod
    def put(self, content, file_path):
        pass

    @abc.abstractmethod
    def replace(self, file_path):
        pass

    @abc.abstractmethod
    def delete(self, _id):
        pass
