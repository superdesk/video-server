import json
import logging
import os
import shlex
import subprocess

from flask import current_app as app

from videoserver.lib.utils import create_temp_file
from .interface import VideoEditorInterface

logger = logging.getLogger(__name__)


class FFMPEGVideoEditor(VideoEditorInterface):
    """
    FFMPEG based video editor

    Links:
      https://ffmpeg.org/ffmpeg.html#Detailed-description
      http://ffmpeg.org/ffmpeg.html#Generic-options
      http://ffmpeg.org/ffmpeg.html#Main-options
      https://ffmpeg.org/ffmpeg.html#Stream-copy
      https://ffmpeg.org/ffmpeg-filters.html
      https://ffmpeg.org/ffmpeg-filters.html#crop
      https://ffmpeg.org/ffmpeg-all.html#transpose
      http://ffmpeg.org/ffmpeg-filters.html#scale
      https://trac.ffmpeg.org/wiki/Scaling
    """

    def get_meta(self, filestream, extension='tmp'):
        """
        Use ffmpeg tool for getting metadata of file
        :param filestream: file to get meta from
        :type filestream: bytes
        :return: metadata
        :rtype: dict
        """

        file_temp_path = create_temp_file(filestream)
        try:
            metadata = self._get_meta(file_temp_path)
        finally:
            os.remove(file_temp_path)

        return metadata

    def edit_video(self, stream_file, filename, trim=None, crop=None, rotate=None, scale=None):
        """
        Use ffmpeg tool for edit video
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

        # file extension is required by ffmpeg
        path_input = create_temp_file(stream_file, suffix=f".{filename.rsplit('.', 1)[-1]}")
        path_output = '{}_edit.{}'.format(*path_input.rsplit('.', 1))
        filter_string = ''
        try:
            # get option for trim
            trim_option = (
                '-ss', str(trim['start']),
                '-t', str(trim['end'] - trim['start']),
                '-qscale', '0',
            ) if trim else tuple()
            # crop
            # https://ffmpeg.org/ffmpeg-filters.html#crop
            if crop:
                filter_string += f'crop={crop["width"]}:{crop["height"]}:{crop["x"]}:{crop["y"]}'
            # scale
            # http://ffmpeg.org/ffmpeg-filters.html#scale
            # https://trac.ffmpeg.org/wiki/Scaling
            if scale:
                filter_string += ',' if filter_string != '' else ''
                # avoid width not divisible by 2
                if scale % 2 == 1:
                    scale -= 1
                filter_string += f"scale={scale}:-2"
            # rotate
            # https://ffmpeg.org/ffmpeg-all.html#transpose
            # 0 = 90CounterCLockwise and Vertical Flip (default)
            # 1 = 90Clockwise
            # 2 = 90CounterClockwise
            # 3 = 90Clockwise and Vertical Flip
            if rotate:
                rotate_string = ''
                if rotate == 90:
                    rotate_string = 'transpose=1'
                elif rotate == -90:
                    rotate_string = 'transpose=2'
                elif rotate == 180:
                    rotate_string = 'transpose=1,transpose=1'
                elif rotate == -180:
                    rotate_string = 'transpose=2,transpose=2'
                elif rotate == 270:
                    rotate_string = 'transpose=1,transpose=1,transpose=1'
                elif rotate == -270:
                    rotate_string = 'transpose=2,transpose=2,transpose=2'
                filter_string += ',' if filter_string != '' else ''
                filter_string += rotate_string
            # get option for filter
            filter_option = ('-filter:v', filter_string) if filter_string else tuple()
            # run ffmpeg
            if filter_option or trim_option:
                # combine trim and filter to run one time
                self._run_ffmpeg(
                    path_input=path_input,
                    path_output=path_output,
                    options=(
                        *trim_option,
                        *filter_option,
                        '-threads', str(app.config.get('FFMPEG_THREADS')),
                        '-preset', app.config.get('FFMPEG_PRESET')
                    )
                )
            content = open(path_input, 'rb+').read()
            metadata_edit_file = self._get_meta(path_input)
        finally:
            if path_input:
                os.remove(path_input)
        return content, metadata_edit_file

    def capture_thumbnail(self, stream_file, filename, duration, position, crop=None, rotate=0):
        """
        Use ffmpeg tool to capture video frame at a position.
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

        path_video = create_temp_file(stream_file)
        try:
            # avoid the last frame, it is null
            if int(duration) <= int(position):
                position = duration - 0.1
            # create output file path
            output_file = f"{path_video}_preview_thumbnail.png"

            vfilter = ''
            if crop:
                vfilter = f'-vf crop={crop["width"]}:{crop["height"]}:{crop["x"]}:{crop["y"]}'
            if rotate:
                vfilter += ',' if vfilter else '-vf '
                transpose = 'transpose=1' if rotate > 0 else 'transpose=2'
                vfilter += ','.join([transpose] * abs(rotate // 90))

            try:
                # run ffmpeg command
                self._run_ffmpeg(
                    path_input=path_video,
                    path_output=output_file,
                    preoptions=('-y', '-accurate_seek'),
                    options=(
                        '-ss', str(position),
                        '-vframes', '1',
                        *shlex.split(vfilter),
                    ),
                    override=False,
                )
                # get metadata
                thumbnail_metadata = self._get_meta(output_file)
                thumbnail_metadata['mimetype'] = 'image/png'
                # read binary
                with open(output_file, "rb") as f:
                    content = f.read()
                return content, thumbnail_metadata
            finally:
                if os.path.exists(output_file):
                    # delete temp thumbnail file
                    os.remove(output_file)
        finally:
            os.remove(path_video)

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

        path_video = create_temp_file(stream_file)
        try:
            # time period between two frames
            if thumbnails_amount == 1:
                frame_per_second = (duration - 0.05)
            else:
                frame_per_second = (duration - 0.05) / (thumbnails_amount - 1)

            # capture list frame via script capture_list_frames.sh
            path_script = os.path.dirname(__file__) + '/script/capture_list_frames.sh'
            # create output file path
            output_file = f"{path_video}_"
            # subprocess bash -> ffmpeg in the loop
            subprocess.run([path_script, path_video, output_file, str(frame_per_second), str(thumbnails_amount)])
            for i in range(0, thumbnails_amount):
                thumbnail_path = f'{output_file}{i}.png'
                try:
                    # get metadata
                    thumbnail_metadata = self._get_meta(thumbnail_path)
                    thumbnail_metadata['mimetype'] = 'image/png'
                    # read binary
                    with open(thumbnail_path, "rb") as f:
                        content = f.read()
                    yield content, thumbnail_metadata
                finally:
                    # delete temp thumbnail file
                    os.remove(thumbnail_path)
        finally:
            os.remove(path_video)

    def _run_ffmpeg(self, path_input, path_output, preoptions=tuple(), options=tuple(), override=True):
        """
        Subprocess `ffmpeg` command.
        :param path_input: input file path
        :type path_input: str
        :param path_output: outut file path
        :type path_output: str
        :param preoptions: options apply for input file
        :type preoptions: tuple
        :param options: options for ffmpeg cmd
        :type options: tuple
        :param override: replace input file with output file
        :type override: bool
        :return: file path to edited file
        :rtype: str
        """
        try:
            # run ffmpeg with provided options
            subprocess.run(["ffmpeg", "-loglevel", "error", *preoptions, "-i", path_input, *options, path_output])
            if not override:
                return path_output
            # replace tmp origin
            subprocess.run(["cp", "-r", path_output, path_input])
            return path_input
        finally:
            if override:
                # delete old tmp input file
                os.remove(path_output)

    def _get_meta(self, file_path):
        """
        Get metada using `ffprobe` command
        :param file_path: path to a file to retrieve a metadata
        :type file_path: str
        :return: metadata
        :rtype: dict
        """

        cmd = ('ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', file_path)
        with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
            (output, _) = proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"Subprocess with command: '{cmd}' has failed.")

        video_data = json.loads(output.decode("utf-8"))

        for stream in video_data['streams']:
            if stream['codec_type'] == 'video':
                data = stream
                break
        else:
            raise Exception(f'codec_type "video" was not found in streams. '
                            f'Streams: {video_data["streams"]}. '
                            f'File: {file_path}')

        video_meta_keys = ('codec_name', 'codec_long_name', 'width', 'height', 'r_frame_rate', 'bit_rate',
                           'nb_frames', 'duration')

        metadata = {key: data.get(key) for key in video_meta_keys}
        metadata['format_name'] = video_data['format']['format_name']
        metadata['size'] = video_data['format']['size']

        # some videos don't have duration in video stream
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
