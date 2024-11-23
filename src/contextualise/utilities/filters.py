"""
filters.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from ..topic_store import get_topic_store


def topic_name(topic_identifier: str, topic_map_identifier: int) -> str:
    topic_store = get_topic_store()
    topic = topic_store.get_topic(topic_map_identifier, topic_identifier)
    if topic:
        return topic.first_base_name.name

    parts = [part.capitalize() for part in topic_identifier.split("-")]
    return " ".join(parts)


def bitwise_and(value1: int, value2: int) -> int:
    return value1 & value2


def truncate_words(text: str, max_words: int) -> str:
    """
    Truncate a string to a specified number of words, followed by '...'.
    :param text: The input string to truncate.
    :param num_words: The number of words to keep before truncating.
    :return: Truncated string with ellipsis if longer than num_words.
    """

    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."
    return text


def register_filters(app):
    app.jinja_env.filters["topic_name"] = topic_name
    app.jinja_env.filters["bitwise_and"] = bitwise_and
    app.jinja_env.filters["truncate_words"] = truncate_words
