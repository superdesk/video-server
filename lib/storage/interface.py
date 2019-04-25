import abc


class MediaStorageInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, _id):
        pass

    @abc.abstractmethod
    def get_record(self, _id):
        pass

    @abc.abstractmethod
    def get_file(self, doc):
        pass

    @abc.abstractmethod
    def put(self, content, filename, metadata, mime_type, type='video', **kwargs):
        pass

    @abc.abstractmethod
    def edit(self, content, filename, metadata, mime_type, type='video', **kwargs):
        pass

    @abc.abstractmethod
    def delete(self, _id):
        pass
