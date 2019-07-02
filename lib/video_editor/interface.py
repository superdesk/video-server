import abc


class VideoEditorInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_meta(self, filestream):
        pass

    @abc.abstractmethod
    def edit_video(self, stream_file, filename, trim=None, crop=None, rotate=None, scale=None):
        pass

    @abc.abstractmethod
    def capture_thumbnail(self, stream_file, filename, duration, position):
        pass

    @abc.abstractmethod
    def capture_timeline_thumbnails(self, stream_file, filename, duration, thumbnails_amount):
        pass
