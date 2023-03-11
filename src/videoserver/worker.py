import logging

from .app import get_app

logger = logging.getLogger(__name__)
celery = get_app().celery
