"""
topic_store.py file. Part of the Contextualise project.

March 5, 2019
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""


from flask import current_app, g
from topicdb.core.store.topicstore import TopicStore


def get_topic_store():
    if "topic_store" not in g:
        g.topic_store = TopicStore(database_path=current_app.config["DATABASE_PATH"])
    return g.topic_store


# Explicitly closing the connection at the end of each request is unnecessary
# as the topic store manages its own connections

# def close_topic_store(e=None):
#     topic_store = g.pop("topic_store", None)
#     if topic_store is not None:
#         topic_store.close()  # Close all the connections
#         current_app.logger.warning(f"Topic store has been closed")


# def init_app(app):
#     app.teardown_appcontext(close_topic_store)
