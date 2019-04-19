import os
import subprocess as cmd
from io import BytesIO
import uuid
import tempfile


class VideoEditor(object):

    def get_meta(self):
        pass

    def create_video(self):
        pass

    def edit_video(self):
        pass


class FfmpegVideoEditor(VideoEditor):
    def get_meta(self, file):
        ext = file.filename.split('.')
        file_name = "%s.%s" % (uuid.uuid4().hex, ext)
        metadata = {}
        try:
            file_temp_path = self.create_temp_file(file.stream, file_name)
            metadata = self._get_meta(file_temp_path)
        finally:
            if file_temp_path:
                os.remove(file_temp_path)
        return metadata

    def create_video(self, file):
        ext = file.filename.split('.')
        file_name = "%s.%s" % (uuid.uuid4().hex, ext)
        try:
            file_temp_path = self.create_temp_file(file.stream, file_name)
            metadata = self._get_meta(file_temp_path)
        finally:
            if file_temp_path:
                os.remove(file_temp_path)

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
            ["ffprobe", '-show_streams', '/home/thanhnguyen/PycharmProjects/0_test/video/video.mp4'],
            stdout=cmd.PIPE)
        data = res.communicate()[0].decode("utf-8").split('\n')
        metadata = {}
        for text in data:
            info = text.split('=')
            if len(info) == 2:
                metadata[info[0]] = info[1]
        return metadata

    def create_temp_file(self, file_stream, file_name):
        """
            Get stream file from resource and save it to /tmp directory for using (cutting and capture)
        :param media_id:
        :return:
        """
        tmp_path = tempfile.gettempdir() + "/tmp_%s" % file_name
        with open(tmp_path, "wb") as f:
            f.write(file_stream.read())
        return tmp_path


class MoviePyVideoEditor(VideoEditor):
    pass


class VideoEditorFactory():
    def get_video_editor_tool(self, name):
        if name == 'ffmpeg':
            return FfmpegVideoEditor()
        if name == 'moviepy':
            return MoviePyVideoEditor()
        return None


def get_video_editor_tool(name):
    return VideoEditorFactory().get_video_editor_tool(name)
