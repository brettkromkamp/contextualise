"""
topic_store.py file. Part of the Contextualise project.

March 5, 2019
Brett Alistair Kromkamp (brett.kromkamp@gmail.com)
"""

from flask import current_app, g

from topicdb.core.store.topicstore import TopicStore


def get_topic_store():
    if "topicstore" not in g:
        g.topic_store = TopicStore(
            current_app.config["TOPIC_STORE_USER"],
            current_app.config["TOPIC_STORE_PASSWORD"],
            dbname=current_app.config["TOPIC_STORE_DBNAME"],
        )
        g.topic_store.open()
    return g.topic_store


def close_topic_store(e=None):
    topic_store = g.pop("topicstore", None)
    if topic_store is not None:
        topic_store.close()


def init_app(app):
    app.teardown_appcontext(close_topic_store)
