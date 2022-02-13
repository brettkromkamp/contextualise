"""
filters.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from contextualise.topic_store import get_topic_store


def topic_name(topic_identifier, topic_map_identifier):
    result = "Undefined"
    topic_store = get_topic_store()
    topic = topic_store.get_topic(topic_map_identifier, topic_identifier)
    if topic:
        result = topic.first_base_name.name
    return result


def bitwise_and(value1, value2):
    return value1 & value2


def register_filters(app):
    app.jinja_env.filters["topic_name"] = topic_name
    app.jinja_env.filters["bitwise_and"] = bitwise_and
