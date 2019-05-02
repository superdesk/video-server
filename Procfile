rest: gunicorn -c gunicorn_config.py -b "0.0.0.0:5050" wsgi
work: celery -A worker worker
