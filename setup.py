import os
import platform
import sys

from setuptools import find_packages
from setuptools import setup


if sys.version_info < (3, 7):
    raise Exception("RestCatalyst requires Python 3.7 or higher.")

cpython = platform.python_implementation() == "CPython"



def status_msgs(*msgs):
    print("*" * 75)
    for msg in msgs:
        print(msg)
    print("*" * 75)



with open(os.path.join(os.path.dirname(__file__), "README.md")) as r_file:
    readme = r_file.read()


def run_setup():
    kwargs = {}


    setup(
        name="RestCatalyst",
        version=0.1,
        description="Restful API Catalyst",
        author="Kamyar Inanloo",
        author_email="kamyar1979@gmail.com",
        url="http://kamyar.tel",
        project_urls={
            "Documentation": "https://docs.sqlalchemy.org",
        },
        packages=find_packages("lib"),
        package_dir={"": "lib"},
        license="BSD",
        long_description=readme,
        python_requires=">=3.7",
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
        ],
        **kwargs
    )


if not cpython:
    run_setup()
