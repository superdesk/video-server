import os
import shutil

import pytest

from app import get_app


@pytest.fixture(scope='function')
def test_app(request):
    """
    Main test app fixture.

    :return: flask app
    """
    test_app = get_app()
    test_app.config['TESTING'] = True
    test_app.config['MONGO_DBNAME'] = 'sd_video_editor_test'
    test_app.config['MONGO_URI'] = 'mongodb://localhost:27017/sd_video_editor_test'
    test_app.config['FS_MEDIA_STORAGE_PATH'] = os.path.join(os.path.dirname(__file__), 'media', 'projects')

    if not os.path.exists(test_app.config['FS_MEDIA_STORAGE_PATH']):
        os.makedirs(test_app.config['FS_MEDIA_STORAGE_PATH'])

    test_app.init_db()

    def test_app_teardown():
        """
        Remove test folder and drop test db
        """
        # drop test db
        test_app.mongo.db.projects.drop()
        # drop test media folder
        if os.path.exists(test_app.config['FS_MEDIA_STORAGE_PATH']):
            shutil.rmtree(os.path.dirname(test_app.config.get('FS_MEDIA_STORAGE_PATH')))

    request.addfinalizer(test_app_teardown)

    return test_app


@pytest.fixture(scope='function')
def client(test_app):
    client = test_app.test_client()

    with test_app.app_context():
        yield client


@pytest.fixture(scope='function')
def filestreams(request):
    filestreams = []

    for filename in request.param:
        test_path = os.path.dirname(os.path.abspath(__file__))
        with open(f'{test_path}/storage/fixtures/{filename}', 'rb') as f:
            filestream = f.read()
        filestreams.append(filestream)

    return filestreams
