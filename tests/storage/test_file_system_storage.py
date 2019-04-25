import os
import shutil

from lib.storage.file_system_storage import FileSystemStorage

storage = FileSystemStorage()


def test_put_file_system_storage(test_app, client, filestream):
    filename = 'test_fs_media_storage'
    doc = storage.put(filestream, filename, None, 'mp4')
    filename = doc.get('filename')
    dir_file = doc.get('folder')
    file_path = "%s/%s/%s" % (test_app.config.get('FS_MEDIA_STORAGE_PATH'), dir_file, filename)

    assert doc['filename'] == filename
    assert doc['metadata'] is None
    assert doc['mime_type'] == 'mp4'
    assert os.path.exists(file_path) is True

    # TODO use some kind of teardown here
    # we should configure setup/teardown for every test
    # here we simply should drop entire collection and temp folder
    # every test MUST be independent
    # see teardown hooks
    test_app.mongo.db.projects.drop()
    shutil.rmtree(os.path.dirname(test_app.config.get('FS_MEDIA_STORAGE_PATH')))
