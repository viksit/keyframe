# pymyra installation and build/release

import os
import sys
from os import chdir, system
from os.path import abspath, dirname, join, normpath
from subprocess import call
from sys import exit, version_info
from setuptools import setup, find_packages, Command
from os.path import expanduser, join

from pymyra import __version__

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    from distutils.command.build_py import build_py

install_requires = [
    "requests>=2.11.1"
]
conf_file_location = join(expanduser("~"), ".pymyra")

setup(
    name = "pymyra",
    version = __version__,
    description = "Myra SDK for Python 2.x.",
    author = "The Myra Team",
    author_email = "info@myralabs.com",
    url = "https://github.com/myralabs/python-myra",
    cmdclass={"build_py": build_py},
    install_requires=install_requires,
    packages=find_packages(),
    data_files=[(conf_file_location, ["pymyra/settings.conf"])]
)
