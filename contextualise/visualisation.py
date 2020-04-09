import maya
from flask import Blueprint, render_template
from flask_login import current_user
from topicdb.core.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint("visualisation", __name__)

UNIVERSAL_SCOPE = "*"


@bp.route("/visualisations/network/<map_identifier>/<topic_identifier>")
def network(map_identifier, topic_identifier):
    topic_store = get_topic_store()

    collaboration_mode = None
    if current_user.is_authenticated:  # User is logged in
        is_map_owner = topic_store.is_topic_map_owner(map_identifier, current_user.id)
        if is_map_owner:
            topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
        else:
            topic_map = topic_store.get_topic_map(map_identifier)
        if topic_map is None:
            abort(404)
        collaboration_mode = topic_store.get_collaboration_mode(map_identifier, current_user.id)
        # The map is private and doesn't belong to the user who is trying to access it
        if not topic_map.published and not is_map_owner:
            if not collaboration_mode:  # The user is not collaborating on the map
                abort(403)
    else:  # User is not logged in
        topic_map = topic_store.get_topic_map(map_identifier)
        if topic_map is None:
            abort(404)
        if not topic_map.published:  # User is not logged in and the map is not published
            abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    return render_template(
        "visualisation/network.html",
        topic_map=topic_map,
        topic=topic,
        creation_date=creation_date,
        collaboration_mode=topic_map.collaboration_mode,
    )


@bp.route("/visualisations/timeline/<map_identifier>/<topic_identifier>")
def timeline(map_identifier, topic_identifier):
    topic_store = get_topic_store()

    collaboration_mode = None
    if current_user.is_authenticated:  # User is logged in
        is_map_owner = topic_store.is_topic_map_owner(map_identifier, current_user.id)
        if is_map_owner:
            topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
        else:
            topic_map = topic_store.get_topic_map(map_identifier)
        if topic_map is None:
            abort(404)
        collaboration_mode = topic_store.get_collaboration_mode(map_identifier, current_user.id)
        # The map is private and doesn't belong to the user who is trying to access it
        if not topic_map.published and not is_map_owner:
            if not collaboration_mode:  # The user is not collaborating on the map
                abort(403)
    else:  # User is not logged in
        topic_map = topic_store.get_topic_map(map_identifier)
        if topic_map is None:
            abort(404)
        if not topic_map.published:  # User is not logged in and the map is not published
            abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    return render_template(
        "visualisation/timeline.html",
        topic_map=topic_map,
        topic=topic,
        creation_date=creation_date,
        collaboration_mode=topic_map.collaboration_mode,
    )


@bp.route("/visualisations/map/<map_identifier>/<topic_identifier>")
def map(map_identifier, topic_identifier):  # TODO: Shadows built-in name 'map'. Rename?
    topic_store = get_topic_store()

    collaboration_mode = None
    if current_user.is_authenticated:  # User is logged in
        is_map_owner = topic_store.is_topic_map_owner(map_identifier, current_user.id)
        if is_map_owner:
            topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
        else:
            topic_map = topic_store.get_topic_map(map_identifier)
        if topic_map is None:
            abort(404)
        collaboration_mode = topic_store.get_collaboration_mode(map_identifier, current_user.id)
        # The map is private and doesn't belong to the user who is trying to access it
        if not topic_map.published and not is_map_owner:
            if not collaboration_mode:  # The user is not collaborating on the map
                abort(403)
    else:  # User is not logged in
        topic_map = topic_store.get_topic_map(map_identifier)
        if topic_map is None:
            abort(404)
        if not topic_map.published:  # User is not logged in and the map is not published
            abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    return render_template(
        "visualisation/map.html",
        topic_map=topic_map,
        topic=topic,
        creation_date=creation_date,
        collaboration_mode=topic_map.collaboration_mode,
    )
