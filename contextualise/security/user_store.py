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


SETTINGS_FILE_PATH = os.path.join(os.path.dirname(__file__), "../../instance/settings.ini")

config = configparser.ConfigParser()
config.read(SETTINGS_FILE_PATH)

database_path = os.path.join(os.path.dirname(__file__), "../../instance", config["DATABASE"]["Filename"])

engine = create_engine(f"sqlite:///{database_path}")
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    Base.metadata.create_all(bind=engine)
