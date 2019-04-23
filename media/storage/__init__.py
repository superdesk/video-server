from . import fs_media_storage


def get_media_storage(name):
    if str.lower(name) == 'filesystem':
        return fs_media_storage.FileSystemMediaStorage
    if str.lower(name) == 'amazon':
        return None
    return None
