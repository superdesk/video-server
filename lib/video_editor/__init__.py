from .ffmpeg import FFMPEGVideoEditor
from .moviepy import MoviePyVideoEditor
from flask import current_app as app


def get_video_editor(name=None):
    # Set default tool for video editor
    if not name:
        name = app.config.get("DEFAULT_MEDIA_TOOL")
    if name == 'ffmpeg':
        return FFMPEGVideoEditor()
    if name == 'moviepy':
        return MoviePyVideoEditor()
    return None
