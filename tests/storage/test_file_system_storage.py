import os

from lib.storage.file_system_storage import FileSystemStorage

storage = FileSystemStorage()


def test_put_file_system_storage(test_app, client, filestream):
    filename = 'test_fs_media_storage.mp4'
    storage_id = storage.put(filestream, filename, 'video/mp4')
    assert os.path.exists(
        os.path.join(test_app.config['FS_MEDIA_STORAGE_PATH'], storage_id))
