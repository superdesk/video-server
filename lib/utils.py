import uuid
import datetime
import os


def create_file_name(ext):
    return "%s.%s" % (uuid.uuid4().hex, ext)


def get_path_group_by_year_month(filename, date):
    year = date.year
    month = date.month
    return "%s/%s/%s" % (year, month, filename)
