from celery import Celery
from werkzeug.exceptions import InternalServerError
from kombu.serialization import register
from bson import json_util

from .lib.logging import logger

celery = Celery(__name__)
TaskBase = celery.Task


def encoder(obj):
    return json_util.dumps(obj)


def decoder(s):
    return json_util.loads(s)


register('bson', encoder=encoder, decoder=decoder, content_type='application/json')


def init_celery(app):

    class ContextTask(TaskBase):
        """
        Enhance `celery.Task` by wrapping the task execution in a flask application context.
        """

        # https://docs.celeryproject.org/en/latest/reference/celery.app.task.html#celery.app.task.Task.abstract
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                try:
                    return super().__call__(*args, **kwargs)
                except InternalServerError as e:
                    handle_exception(e)

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            with app.app_context():
                handle_exception(exc)

    celery.Task = ContextTask
    celery.config_from_object(app.config, namespace='CELERY')
    app.init_db()
    app.celery = celery


def handle_exception(exc):
    """Log exception to logger."""
    logger.exception(exc)
