import os
import pytest
import shutil

from media import get_media_collection
from media.storage.fs_media_storage import FileSystemMediaStorage

storage = FileSystemMediaStorage()


def test_put_fs_media_storage(client, filestream):
    from media.storage import fs_media_storage
    fs_media_storage.PATH_FS = os.path.dirname(__file__) + '/fs'
    filename = 'test_fs_media_storage'
    doc = storage.put(filestream, filename, None, 'mp4')
    filename = doc.get('filename')
    dir_file = doc.get('folder')
    file_path = "%s/%s/%s" % (fs_media_storage.PATH_FS, dir_file, filename)
    assert doc['filename'] == filename
    assert doc['mime_type'] == 'mp4'
    assert os.path.exists(file_path) is True
    get_media_collection().delete_one({'_id': doc['_id']})
    shutil.rmtree(fs_media_storage.PATH_FS)
