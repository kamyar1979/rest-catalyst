import os
import sys

from setuptools import find_packages
from setuptools import setup


if sys.version_info < (3, 7):
    raise Exception("RestCatalyst requires Python 3.7 or higher.")


with open(os.path.join(os.path.dirname(__file__), "README.md")) as r_file:
    readme = r_file.read()



setup(
    name="RestCatalyst",
    version="1.1.9",
    platforms="Any",
    description="Restful API Catalyst",
    author="Kamyar Inanloo",
    author_email="kamyar1979@gmail.com",
    url="http://kamyar.tel",
    project_urls={
        "Documentation": "https://docs.sqlalchemy.org",
    },
    packages=find_packages(),
    license="BSD",
    long_description=readme,
    python_requires=">=3.7",
    install_requires=[
        'setuptools',
        'geojson',
        'pytz',
        'SQLAlchemy_Utils',
        'Khayyam',
        'Cerberus',
        'toolz',
        'python_rapidjson',
        'SQLAlchemy',
        'typing',
        'cbor',
        'pyparsing',
        'u_msgpack_python',
        'GeoAlchemy2',
        'Flask',
        'Shapely',
        'ntplib',
        'rapidjson',
        'umsgpack',
        'json2html'
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Database :: Front-Ends",
        "Operating System :: OS Independent",
    ])


