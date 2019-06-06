import json
import os
import subprocess as cmd
import tempfile
from io import BytesIO

from lib.utils import create_file_name

from .interface import VideoEditorInterface


class FFMPEGVideoEditor(VideoEditorInterface):

    def get_meta(self, filestream, extension='tmp'):
        """
        Use ffmpeg tool for getting metadata of video file
        :param filestream:
        :return:
        """
        file_name = create_file_name(extension)
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
        :param stream_file:
        :param filename:
        :param metadata:
        :param video_cut:
        :param video_crop:
        :param video_rotate:
        :param video_quality:
        :return:
        """
        path_video = ''
        try:
            path_video = self._create_temp_file(stream_file, filename)

            if not metadata:
                metadata = self._get_meta(path_video)

            duration = float(metadata['duration'])
            if (not video_cut or (video_cut['start'] == 0 and int(video_cut['end']) == int(duration))) \
                    and not video_crop \
                    and (not video_rotate or int(video_rotate['degree']) % 360 == 0) \
                    and not video_quality:
                return None, {}
            path_output = path_video + "_edit" + os.path.splitext(filename)[1]
            # use copy data
            # set option and run cut first
            if video_cut:
                path_video = self._edit_video(path_video, path_output,
                                              ["-ss", str(video_cut["start"]), "-t",
                                               str(int(video_cut["end"]) - int(video_cut["start"])), "-c", "copy"])

            # use filter data
            str_filter = ""
            # set option for crop
            if video_crop:
                # get max width, height if crop over the video
                if int(video_crop.get('width')) > int(metadata.get('width')):
                    video_crop['width'] = int(metadata.get('width'))
                if int(video_crop.get('height')) > int(metadata.get('height')):
                    video_crop['height'] = int(metadata.get('height'))
                str_filter += "crop=%s:%s:%s:%s" % (
                    video_crop["width"], video_crop["height"], video_crop["x"], video_crop["y"])
            # set option for rotate
            if video_rotate:
                delta90 = round((int(video_rotate['degree'] % 360) / 90))
                if delta90 != 0:
                    rotate_string = ''
                    if delta90 == 1:
                        rotate_string = "transpose=1"
                    if delta90 == 2:
                        rotate_string = "transpose=2,transpose=2"
                    if delta90 == 3:
                        rotate_string = "transpose=2"
                    str_filter += "," if str_filter != "" else ''
                    str_filter += rotate_string
            # set option for quality
            if video_quality:
                str_filter += "," if str_filter != "" else ''
                str_filter += "scale=%s:-2" % video_quality['quality']
            if str_filter != '':
                path_video = self._edit_video(path_video, path_output,
                                              ["-filter:v", str_filter, "-max_muxing_queue_size", "1024", "-threads",
                                               "5", "-preset", "ultrafast", "-strict", "-2", "-c:a", "copy"
                                               ])
            content = open(path_video, "rb+").read()
            metadata_edit_file = self._get_meta(path_video)
        finally:
            if path_video:
                os.remove(path_video)
        return content, metadata_edit_file

    def capture_thumbnail(self, stream_file, filename, metadata, capture_time):
        """
        Use ffmpeg tool to capture video at a time.
        :param stream_file: binary file stream
        :param filename: name of edit video, not path
        :param metadata: a dictionary, contain metadata edited video
        :param capture_time: type int, time for capture
        :return: stream file and dictionary info of metadata of edit video
        """
        path_video = ''
        try:
            path_video = self._create_temp_file(stream_file, filename)
            duration = float(metadata['duration'])
            path_output = path_video + "_thumbnail.png"
            # avoid the end frame, is null
            if int(duration) <= int(capture_time):
                capture_time = duration - 0.1
            content = self._capture_thumbnail(path_video, path_output, capture_time)
            thumbnail_metadata = self._get_meta(path_output)
        finally:
            if path_video:
                os.remove(path_video)
            if path_output:
                os.remove(path_output)
        return content, thumbnail_metadata

    def capture_list_timeline_thumbnails(self, stream_file, filename, metadata, number_frames):
        """
        Capture a list frames in all play time of video.
        :param stream_file: binary file stream
        :param filename: name of edit video, not path
        :param metadata:  a dictionary, contain metadata edited video
        :param number_frames: total number frames capture
        :return:
        """
        path_video = ''
        try:
            path_video = self._create_temp_file(stream_file, filename)
            duration = float(metadata['duration'])
            # period time between two frames

            if number_frames == 1:
                frame_per_second = (duration - 1)
            else:
                frame_per_second = (duration - 1) / (number_frames - 1)

            # capture list frame via script capture_list_frames.sh
            path_script = os.path.dirname(__file__) + '/script/capture_list_frames.sh'
            cmd.run([path_script, path_video, path_video + "_", str(frame_per_second), str(number_frames)])
            for i in range(0, number_frames):
                path_output = path_video + '_%0d.bmp' % i
                try:
                    thumbnail_metadata = self._get_meta(path_output)
                    thumbnail_metadata['mimetype'] = 'image/bmp',
                    yield open(path_output, "rb+").read(), thumbnail_metadata
                finally:
                    os.remove(path_output)
        finally:
            if path_video:
                os.remove(path_video)

    def _capture_thumbnail(self, path_video, path_output, time_capture=0):
        """
            Use ffmpeg to capture video at a time.
        :param path_video:
        :param path_output:
        :param time_capture:
        :return:
        """
        cmd.run(["ffmpeg", "-v", "error", "-y", "-accurate_seek", "-i", path_video,
                 "-ss", str(time_capture), "-vframes", "1", path_output])
        return open(path_output, "rb+").read()

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
            cmd.run(["ffmpeg", "-v", "error", "-i", path_video, *para, path_output])

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
            ['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', path_video],
            stdout=cmd.PIPE)
        result = res.communicate()[0].decode("utf-8")
        video_data = json.loads(result)

        data = None
        for stream in video_data['streams']:
            if stream['codec_type'] == 'video' or not data:
                data = stream

        format_meta = ('format_name', 'size')
        video_meta = ('codec_name', 'codec_long_name', 'width', 'height', 'r_frame_rate', 'bit_rate',
                      'nb_frames', 'duration')

        metadata = {key: data.get(key) for key in video_meta}
        metadata['format_name'] = video_data['format']['format_name']
        metadata['size'] = video_data['format']['size']

        # some video don't have duration in video stream
        if not metadata['duration']:
            metadata['duration'] = video_data['format'].get('duration')

        # ffmpeg output some number type as string
        format_type = {
            'size': int,
            'bit_rate': int,
            'nb_frames': int,
            'duration': float,
        }
        for value in format_type:
            if metadata.get(value):
                metadata[value] = format_type[value](metadata[value])

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
