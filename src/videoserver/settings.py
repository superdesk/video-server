import os
from distutils.util import strtobool as _strtobool


def strtobool(value):
    try:
        return bool(_strtobool(value))
    except ValueError:
        return False


def env(variable, fallback_value=None):
    if os.environ.get('VIDEO_SERVER_USE_DEFAULTS'):
        return fallback_value

    env_value = os.environ.get(variable)
    if env_value is None:
        return fallback_value
    # Next isn't needed anymore
    elif env_value == "__EMPTY__":
        return ''
    else:
        return env_value


def celery_queue(name):
    """Get celery queue name with optional prefix set in environment.

    If you want to use multiple workers in Procfile you have to use the prefix::

        work_publish: celery -A worker -Q "${SUPERDESK_CELERY_PREFIX}publish" worker
        work_default: celery -A worker worker

    :param name: queue name
    """
    return "{}{}".format(os.environ.get('VIDEO_SERVER_CELERY_PREFIX', ''), name)


# base path
BASE_PATH = os.path.dirname(__file__)

#: logging
LOG_CONFIG_FILE = env('LOG_CONFIG_FILE', os.path.join(BASE_PATH, 'logging_config.yml'))

CORE_APPS = [
    'apps.swagger',
    'apps.projects',
]

#: Mongo host port
MONGO_HOST = env('MONGO_HOST', 'localhost')
MONGO_PORT = env('MONGO_PORT', 27017)
MONGO_DBNAME = env('MONGO_DBNAME', 'sd_video_editor')
MONGO_URI = "mongodb://{host}:{port}/{dbname}".format(
    host=MONGO_HOST, port=MONGO_PORT, dbname=MONGO_DBNAME
)

#: rabbit-mq url
RABBIT_MQ_URL = env('RABBIT_MQ_URL', 'pyamqp://guest@localhost//')

#: celery broker
BROKER_URL = env('CELERY_BROKER_URL', RABBIT_MQ_URL)
CELERY_BROKER_URL = BROKER_URL
CELERY_TASK_ALWAYS_EAGER = strtobool(env('CELERY_TASK_ALWAYS_EAGER', 'False'))
CELERY_TASK_SERIALIZER = 'bson'
#: number retry when task fail
MAX_RETRIES = int(env('MAX_RETRIES', 3))
BROKER_CONNECTION_MAX_RETRIES = MAX_RETRIES

#: Codec support
CODEC_SUPPORT_VIDEO = ('vp8', 'vp9', 'h264', 'theora', 'av1')
CODEC_SUPPORT_IMAGE = ('bmp', 'mjpeg', 'png')
CODEC_EXTENSION_MAP = {
    'bmp': 'bmp',
    'png': 'png',
    'mjpeg': 'jpeg'
}
CODEC_MIMETYPE_MAP = {
    'bmp': 'image/bmp',
    'png': 'image/png',
    'mjpeg': 'image/jpeg'
}

#: media storage
MEDIA_STORAGE = env('MEDIA_STORAGE', 'filesystem')
DEFAULT_PATH = os.path.join(BASE_PATH, 'media', 'projects')
FS_MEDIA_STORAGE_PATH = env('FS_MEDIA_STORAGE_PATH', DEFAULT_PATH)

#: media tool
DEFAULT_MEDIA_TOOL = env('DEFAULT_MEDIA_TOOL', 'ffmpeg')

#: pagination, items per page
ITEMS_PER_PAGE = int(env('ITEMS_PER_PAGE', 25))
DEFAULT_TOTAL_TIMELINE_THUMBNAILS = int(env('DEFAULT_TOTAL_TIMELINE_THUMBNAILS', 40))

#: set PORT for video server
VIDEO_SERVER_PORT = env('VIDEO_SERVER_PORT', 5050)

#: use custom url for reading video/picture files. Affects how urls are build in `add_urls`
FILE_STREAM_PROXY_ENABLED = strtobool(env('FILE_STREAM_PROXY_ENABLED', 'False'))
FILE_STREAM_PROXY_URL = env('FILE_STREAM_PROXY_URL', '')

if FILE_STREAM_PROXY_ENABLED and not FILE_STREAM_PROXY_URL:
    raise ValueError('FILE_STREAM_PROXY_URL is required if FILE_STREAM_PROXY_ENABLED')

#: video edit constraints
ALLOW_INTERPOLATION = strtobool(env('ALLOW_INTERPOLATION', 'True'))
INTERPOLATION_LIMIT = env('INTERPOLATION_LIMIT', 1280)
MIN_TRIM_DURATION = env('MIN_TRIM_DURATION', 2)
MIN_VIDEO_WIDTH = env('MIN_VIDEO_WIDTH', 320)
MAX_VIDEO_WIDTH = env('MAX_VIDEO_WIDTH', 3840)
MIN_VIDEO_HEIGHT = env('MIN_VIDEO_HEIGHT', 180)
MAX_VIDEO_HEIGHT = env('MAX_VIDEO_HEIGHT', 2160)

#: ffmpeg command line defaults
# the default is the number of available CPUs (0)
FFMPEG_THREADS = env('FFMPEG_THREADS', '0')
# The default is medium.
# The preset determines how fast the encoding process will be – at the expense of compression efficiency.
# Put differently, if you choose ultrafast, the encoding process is going to run fast,
# but the file size will be larger when compared to medium. The visual quality will be the same.
# Valid presets are ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow and placebo.
FFMPEG_PRESET = env('FFMPEG_PRESET', 'medium')
