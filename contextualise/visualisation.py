import maya
from flask import Blueprint, session, render_template, request, flash, url_for, redirect
from flask_login import current_user
from flask_security import login_required
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint("visualisation", __name__)

UNIVERSAL_SCOPE = "*"


@bp.route("/visualisation/network/<map_identifier>/<topic_identifier>")
def network(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    return render_template("visualisation/network.html", topic_map=topic_map, topic=topic, creation_date=creation_date)


@bp.route("/visualisation/timeline/<map_identifier>/<topic_identifier>")
def timeline(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    return render_template("visualisation/timeline.html", topic_map=topic_map, topic=topic, creation_date=creation_date)


@bp.route("/visualisation/map/<map_identifier>/<topic_identifier>")
def map(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    return render_template("visualisation/map.html", topic_map=topic_map, topic=topic, creation_date=creation_date)
