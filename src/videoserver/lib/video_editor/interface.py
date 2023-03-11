import abc


class VideoEditorInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_meta(self, filestream):
        """
        Get metadata of file
        :param filestream: file to get meta from
        :type filestream: bytes
        :return: metadata
        :rtype: dict
        """
        pass

    @abc.abstractmethod
    def edit_video(self, stream_file, filename, trim=None, crop=None, rotate=None, scale=None):
        """
        Edit video.
        :param stream_file: file to edit
        :type stream_file: bytes
        :param filename: filename for tmp file
        :type filename: str
        :param trim: trim editing rules
        :type trim: dict
        :param crop: crop editing rules
        :type crop: dict
        :param video_rotate: rotate degree
        :type video_rotate: int
        :param scale: width scale to
        :type scale: int
        :return:
        """
        pass

    @abc.abstractmethod
    def capture_thumbnail(self, stream_file, filename, duration, position, crop, rotate):
        """
        Capture video frame at a position.
        :param stream_file: video file
        :type stream_file: bytes
        :param filename: tmp video's file name
        :type filename: str
        :param duration: video's duration
        :type duration: int
        :param position: video position to capture a frame
        :type position: int
        :param crop: crop editing rules
        :type crop: dict
        :param rotate: rotate degree
        :type rotate: int
        :return: file stream, metadata
        :rtype: bytes, dict
        """
        pass

    @abc.abstractmethod
    def capture_timeline_thumbnails(self, stream_file, filename, duration, thumbnails_amount):
        """
        Capture thumbnails for timeline.
        :param stream_file: video file
        :type stream_file: bytes
        :param filename: tmp video's file name
        :type filename: str
        :param duration: video's duration
        :type duration: int
        :param thumbnails_amount: total number of thumbnails to capture
        :type thumbnails_amount: int
        :return: file stream, metadata generator
        :return: bytes, generator
        """
        pass
