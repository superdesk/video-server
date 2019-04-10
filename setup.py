from setuptools import setup, find_packages

package_data = {
    'planning': [
        'templates/*.txt',
        'templates/*.html'
    ]
}

setup(
    name="superdesk-video-server",
    version="0.1",
    packages=find_packages(),
    package_data=package_data,
    include_package_data=True,
    author='IDS team',
    author_email='thanh.nguyentan@idsolutions.com.vn',
    license='MIT',
    install_requires=[
    ],
    url='',
)
