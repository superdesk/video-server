import os
import subprocess as cmd
import tempfile

from io import BytesIO
from media.utils import create_file_name


class VideoEditor(object):

    def get_meta(self, filestream):
        pass

    def edit_video(self, stream_file, filename, metadata, media_id, video_cut=None, video_crop=None, video_rotate=None,
                   video_quality=None):
        pass

    def capture_thumnail(self, filestream, capture_time):
        pass

    def capture_list_timeline_thumnails(self, filestream, number_frames):
        pass


class FfmpegVideoEditor(VideoEditor):

    def get_meta(self, filestream):
        file_name = create_file_name('tmp')
        metadata = {}
        try:
            #: create a temp file
            file_temp_path = self._create_temp_file(filestream, file_name)
            #: get metadata
            metadata = self._get_meta(file_temp_path)
        finally:
            if file_temp_path:
                os.remove(file_temp_path)
        return metadata

    def edit_video(self, stream_file, filename, metadata, media_id, video_cut=None, video_crop=None, video_rotate=None,
                   video_quality=None):
        pass

    def capture_thumnail(self, filestream, capture_time):
        pass

    def capture_list_timeline_thumnails(self, filestream, number_frames):
        pass

    def _capture_thumnail(self, path_video, path_output, time_capture=0):
        """
            Use ffmpeg to capture video at a time.
        :param path_video:
        :param path_output:
        :param time_capture:
        :return:
        """
        try:
            cmd.run(["ffmpeg", "-i", path_video, "-ss", str(time_capture), "-vframes", "1", path_output])
            return BytesIO(open(path_output, "rb+").read())
        finally:
            os.remove(path_output)

    def _edit_video(self, path_video, path_output, para=[]):
        """
             Use ffmpeg to cutting video via start time and end time, and get the total frames of video.
        :param path_video:
        :param path_output:
        :param para:
        :return:
        """
        try:
            # cut video
            cmd.run(["ffmpeg", "-i", path_video, *para, path_output])

            # replace tmp origin
            cmd.run(["cp", "-r", path_output, path_video])
            return path_video
        finally:
            os.remove(path_output)

    def _get_meta(self, path_video):
        """
            Use ffmpeg to capture video at a time.
        :param path_video:
        :param path_output:
        :param time_capture:
        :return:
        """
        res = cmd.Popen(
            ['ffprobe', '-show_streams', '-show_format', path_video],
            stdout=cmd.PIPE)
        data = res.communicate()[0].decode("utf-8").split('\n')
        metadata = {}
        for text in data:
            info = text.split('=')
            if len(info) == 2:
                metadata[info[0]] = info[1]
        res = cmd.Popen(
            ['file', '--mime-type', '-b', path_video],
            stdout=cmd.PIPE)
        mime_type = res.communicate()[0].decode("utf-8").split('\n')
        metadata['mime_type'] = mime_type[0]
        return metadata

    def _create_temp_file(self, file_stream, file_name):
        """
            Get stream file from resource and save it to /tmp directory for using (cutting and capture)
        :param media_id:
        :return:
        """
        tmp_path = tempfile.gettempdir() + "/tmp_%s" % file_name
        with open(tmp_path, "wb") as f:
            f.write(file_stream)
        return tmp_path


class MoviePyVideoEditor(VideoEditor):
    pass
