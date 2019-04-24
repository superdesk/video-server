import os

import pytest

from media import get_media_collection
from media.storage.fs_media_storage import FileSystemMediaStorage

storage = FileSystemMediaStorage()

def test_put_fs_media_storage(client, test_path):
    with open(f'{test_path}/storage/fixtures/sample.mp4', 'rb') as f:
        filestream = f.read()
    filename = 'test_fs_media_storage'
    doc = storage.put(filestream, filename, None, 'mp4')
    
    assert doc['filename'] == filename
    assert doc['metadata'] == None
    assert doc['mime_type'] == 'mp4'

    get_media_collection().delete_one({'_id': doc['_id']})
