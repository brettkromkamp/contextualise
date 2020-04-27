"""
user_store.py file. Part of the Contextualise project.

March 4, 2019
Brett Alistair Kromkamp (brett.kromkamp@gmail.com)
"""

import configparser
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

SETTINGS_FILE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../settings.ini")

config = configparser.ConfigParser()
config.read(SETTINGS_FILE_PATH)

database_username = config["DATABASE"]["Username"]
database_password = config["DATABASE"]["Password"]
database_name = config["DATABASE"]["Database"]
database_host = config["DATABASE"]["Host"]

engine = create_engine(
    f"postgresql://{database_username}:{database_password}@{database_host}/{database_name}",
    pool_size=10,
    max_overflow=20,
    convert_unicode=True,
)
db_session = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    Base.metadata.create_all(bind=engine)
