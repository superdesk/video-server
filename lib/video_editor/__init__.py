from .ffmpeg import FFMPEGVideoEditor
from .moviepy import MoviePyVideoEditor


def get_video_editor_tool(name):
    # TODO this condition must be configurable
    if name == 'ffmpeg':
        return FFMPEGVideoEditor()
    if name == 'moviepy':
        return MoviePyVideoEditor()
    return None
