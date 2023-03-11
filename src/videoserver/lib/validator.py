from cerberus import TypeDefinition, Validator as DefaultValidator
from werkzeug.datastructures import FileStorage as WerkzeugFileStorage


class Validator(DefaultValidator):
    """
    Custom validator with additional types
    """

    types_mapping = DefaultValidator.types_mapping.copy()
    types_mapping['filestorage'] = TypeDefinition('filestorage', (WerkzeugFileStorage,), ())
