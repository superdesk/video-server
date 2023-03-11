from setuptools import setup
from setuptools import find_packages

requirements = (
    'flask>=1.0.2',
    'flask-swagger==0.2.14',
    'Flask-PyMongo==2.2.0',
    'celery>=4.3,<5.0.0',
    'kombu==4.6.11',
    'pytz>=2015.4',
    'pymongo>=3.7.2',
    'cerberus==1.2',
    'PyYAML==5.1'
)

dev_requirements = (
    'flake8',
    'flake8-docstrings',
    'pep8',
    'pyflakes',
    'pydocstyle',
    'pytest==4.4.1',
    'pytest-cov==2.7.1',
    'pytest-pythonpath==0.7.3',
    'tox==3.13.2',
    'tox-pyenv==1.1.0'
)

setup(
    name='videoserver',
    version='1.0.1',
    description='HTTP API video editor.',
    long_description='Friendly HTTP API video editor with pluggable file storage, '
                     'video editing backend, and streaming capabilities.',
    keywords='http api video editor',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Video :: Non-Linear Editor',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Framework :: Flask',

    ],
    url='https://github.com/superdesk/video-server',
    author='Oleg Pshenichniy, Petr Jašek, Loi Tran, Thanh Nguyen',
    author_email='oleg.pshenichniy@sourcefabric.org',
    license='GPLv3',
    install_requires=requirements,
    extras_require={
        'dev': dev_requirements
    },
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.6'
)
