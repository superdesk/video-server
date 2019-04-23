from . import video_editor
import uuid


def get_video_editor_tool(name):
    if name == 'ffmpeg':
        return video_editor.FfmpegVideoEditor()
    if name == 'moviepy':
        return video_editor.MoviePyVideoEditor()
    return None

