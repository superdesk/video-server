import os

bind = '0.0.0.0:%s' % os.environ.get('VIDEO_SERVER_PORT', '5050')
workers = int(os.environ.get('WEB_CONCURRENCY', 2))

accesslog = '-'
access_log_format = '%(m)s %(U)s status=%(s)s time=%(T)ss size=%(B)sb'

reload = True

timeout = int(os.environ.get('WEB_TIMEOUT', 30))