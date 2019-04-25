import os
import subprocess as cmd
import tempfile

from io import BytesIO
from media.utils import create_file_name


class VideoEditor(object):

    def get_meta(self, filestream):
        pass

    def edit_video(self, stream_file, filename, metadata, video_cut=None, video_crop=None, video_rotate=None,
                   video_quality=None):
        pass

    def capture_thumnail(self, filestream, capture_time):
        pass

    def capture_list_timeline_thumnails(self, filestream, number_frames):
        pass


class FfmpegVideoEditor(VideoEditor):

    def get_meta(self, filestream):
        """
        Use ffmpeg tool for getting metadata of video file
        :param filestream:
        :return:
        """
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

    def edit_video(self, stream_file, filename, metadata, video_cut=None, video_crop=None, video_rotate=None,
                   video_quality=None):
        """
        Use ffmpeg tool for edit video
        Support: cut, crop, rotate, quality
        :param stream_file:
        :param filename:
        :param metadata:
        :param media_id:
        :param video_cut:
        :param video_crop:
        :param video_rotate:
        :param video_quality:
        :return:
        """
        try:
            path_video = self._create_temp_file(stream_file, filename)

            if not metadata:
                metadata = self._get_meta(path_video)

            duration = float(metadata['duration'])
            if (not video_cut or (
                    video_cut['start'] == 0 and int(video_cut['end']) == int(duration))) and not video_crop and (
                    not video_rotate or int(video_rotate['degree']) % 360 == 0) and not video_quality:
                return {}
            path_output = path_video + "_edit" + os.path.splitext(filename)[1]
            # use copy data
            if video_cut:
                path_video = self._edit_video(path_video, path_output,
                                              ["-ss", str(video_cut["start"]), "-t",
                                               str(int(video_cut["end"]) - int(video_cut["start"])), "-c", "copy"])

            # use filter data
            str_filter = ""
            if video_crop:
                str_filter += "crop=%s:%s:%s:%s" % (
                    video_crop["width"], video_crop["height"], video_crop["x"], video_crop["y"])
            if video_rotate:
                delta90 = round((int(video_rotate['degree'] % 360) / 90))
                if delta90 != 0:
                    if delta90 == 1:
                        rotate_string = "transpose=1"
                    if delta90 == 2:
                        rotate_string = "transpose=2,transpose=2"
                    if delta90 == 3:
                        rotate_string = "transpose=2"
                    str_filter += "," if str_filter != "" else ''
                    str_filter += rotate_string
            if video_quality:
                str_filter += "," if str_filter != "" else ''
                str_filter += "scale=%s:-2" % video_quality['quality']
            if str_filter != '':
                path_video = self._edit_video(path_video, path_output,
                                              ["-filter:v", str_filter, "-max_muxing_queue_size", "1024", "-threads",
                                               "5",
                                               "-preset", "ultrafast", "-strict",
                                               "-2", "-c:a", "copy"])
            content = open(path_video, "rb+").read()
            metadata_edit_file = self._get_meta(path_video)

        finally:
            if path_video:
                os.remove(path_video)
        return content, metadata_edit_file

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
            print(' '.join(["ffmpeg", "-i", path_video, *para, path_output]))
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
        list_meta = ['height', 'width', 'size', 'bit_rate', 'duration', 'codec_name', 'codec_long_name', 'format_name',
                     'nb_frames']
        for text in data:
            info = text.split('=')
            if len(info) == 2 and info[0] in list_meta and not metadata.get(info[0]):
                metadata[info[0]] = info[1]
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
