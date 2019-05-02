from celery import Celery
celery = Celery(__name__)
TaskBase = celery.Task


def init_celery(app):
    celery.config_from_object(app.config, namespace='CELERY')
    app.celery = celery
