from .ffmpeg import FFMPEGVideoEditor
from .moviepy import MoviePyVideoEditor
from flask import current_app as app


def get_video_editor(name=None):
    # TODO this condition must be configurable
    if name:
        name = app.config.get("DEFAULT_MEDIA_TOOL")
    if name == 'ffmpeg':
        return FFMPEGVideoEditor()
    if name == 'moviepy':
        return MoviePyVideoEditor()
    return None
