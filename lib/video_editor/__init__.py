from flask import current_app as app

from .ffmpeg import FFMPEGVideoEditor
from .moviepy import MoviePyVideoEditor


def get_video_editor(name=None):
    """
    Instantinates and returns selected video editor
    :param name: name of video editor. Options: 'ffmpeg'
    :type name: str
    :return: instance of video editor
    """

    if not name:
        name = app.config.get("DEFAULT_MEDIA_TOOL")

    if name == 'ffmpeg':
        return FFMPEGVideoEditor()
    elif name == 'moviepy':
        return MoviePyVideoEditor()

    raise Exception(f"Video editor backend with '{name}' does not exist.")
