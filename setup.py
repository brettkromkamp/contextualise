"""
setup.py file. Part of the Contextualise project.

March 3, 2019 
Brett Alistair Kromkamp (brett.kromkamp@gmail.com)
"""

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'HISTORY.rst')) as f:
    HISTORY = f.read()

setup(
    name='contextualise',
    version='0.3.0',
    description='Contextualise',
    long_description=README + '\n\n' + HISTORY,
    author='Brett Alistair Kromkamp',
    author_email='brett.kromkamp@gmail.com',
    url='https://github.com/brettkromkamp/contextualise',
    keywords='knowledge management, personal knowledge management, topic map, knowledge graph',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'flask',
        'flask-security',
        'flask-sqlalchemy',
        'sqlalchemy',
        'bcrypt',
        'topic-db',
        'maya',
        'mistune',
        'python-slugify'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Framework :: Flask',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Education'
    ]
)
