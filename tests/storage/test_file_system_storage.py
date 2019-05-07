import os

from lib.storage.file_system_storage import FileSystemStorage

storage = FileSystemStorage()


def test_put_file_system_storage(test_app, filestream):
    file_path = os.path.join(test_app.config.get('FS_MEDIA_STORAGE_PATH'), 'test_fs_media_storage.mp4')
    storage.put(filestream, file_path)
    assert os.path.exists(file_path)
