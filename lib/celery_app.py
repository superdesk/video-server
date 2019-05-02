from celery import Celery
from lib.logging import logger
from werkzeug.exceptions import InternalServerError

celery = Celery(__name__)
TaskBase = celery.Task


def init_celery(app):
    class ContextTask(TaskBase):
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



