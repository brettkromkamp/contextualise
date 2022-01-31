"""
setup.py file. Part of the Contextualise project.

March 3, 2019
Brett Alistair Kromkamp (brett.kromkamp@gmail.com)
"""

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
    README = f.read()
with open(os.path.join(here, "HISTORY.rst"), encoding="utf-8") as f:
    HISTORY = f.read()
with open(os.path.join(here, "requirements.txt")) as f:
    REQUIRED = f.read().splitlines()

setup(
    name="contextualise",
    version="0.4.0",
    description="Contextualise",
    long_description=README + "\n\n" + HISTORY,
    author="Brett Alistair Kromkamp",
    author_email="brett.kromkamp@gmail.com",
    url="https://github.com/brettkromkamp/contextualise",
    keywords="knowledge management, personal knowledge management, topic map, knowledge graph",
    packages=find_packages(),
    package_data={"": ["LICENSE"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIRED,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Framework :: Flask",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Education",
    ],
)
