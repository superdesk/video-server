import abc


class VideoEditorInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_meta(self, filestream):
        pass

    @abc.abstractmethod
    def edit_video(self, stream_file, filename, metadata, video_cut=None, video_crop=None, video_rotate=None,
                   video_quality=None):
        pass

    @abc.abstractmethod
    def capture_thumbnail(self, stream_file, filename, metadata, capture_time):
        pass

    @abc.abstractmethod
    def capture_list_timeline_thumbnails(self, stream_file, filename, metadata, number_frames):
        pass
