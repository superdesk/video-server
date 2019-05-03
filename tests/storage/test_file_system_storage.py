import os

from lib.storage.file_system_storage import FileSystemStorage

storage = FileSystemStorage()


def test_put_file_system_storage(test_app, client, filestream):
    filename = 'test_fs_media_storage'
    storage.put(filestream, filename)
    file_path = "%s/%s" % (test_app.config.get('FS_MEDIA_STORAGE_PATH'), filename)
    assert os.path.exists(file_path) is True
