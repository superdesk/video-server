import json
import logging

from collections import OrderedDict
from flask import current_app as app
import superdesk
from pymongo import MongoClient

logger = logging.getLogger(__name__)


def init_video_database():
    """
    Get info contacts in file and add to database
    :param path_file:
    :param unit_test:
    :return:
    """
    connection = MongoClient(app.config['MONGO_HOST'], app.config['MONGO_PORT'])

    superdeskDb = connection['MONGO_DBNAME']
    superdeskDbCol = superdeskDb['video']
    initdata = {"name": "test"}
    superdeskDbCol.insert_one(initdata)


class VideoInitCommand(superdesk.Command):
    """Import contact from belga to Superdesk.
    This command use for inserting a large number contact from Belga to Superdesk.
    Only support for format json file.
    """

    def run(self):
        logger.info("init video data")
        init_video_database()


superdesk.command('video:init', VideoInitCommand())
