from .file_system_storage import FileSystemStorage


def get_media_storage(name):
    if str.lower(name) == 'filesystem':
        return FileSystemStorage()
    if str.lower(name) == 'amazon':
        return None
    return None
