import abc


class MediaStorageInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, file_path):
        pass

    @abc.abstractmethod
    def put(self, content, file_path):
        pass

    @abc.abstractmethod
    def get_range(self, file_path, start, length):
        pass

    @abc.abstractmethod
    def delete(self, file_path):
        pass
