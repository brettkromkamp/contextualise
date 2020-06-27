import os
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_security import login_required, current_user
from slugify import slugify
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.models.topic import Topic
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint("api", __name__)

SETTINGS_FILE_PATH = os.path.join(os.path.dirname(__file__), "../settings.ini")
UNIVERSAL_SCOPE = "*"


@bp.route("/api/get-slug")
@login_required
def get_slug():
    value = request.args.get("value", "")

    return jsonify({"value": value, "slug": slugify(str(value))})


@bp.route("/api/topic-exists/<map_identifier>")
@login_required
def topic_exists(map_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)

    normalised_topic_identifier = slugify(str(request.args.get("q").lower()))
    normalised_topic_name = " ".join(
        [word.capitalize() for word in normalised_topic_identifier.split("-")]
    )
    exists = topic_store.topic_exists(map_identifier, normalised_topic_identifier)
    if exists:
        result = {"topicExists": True}
    else:
        result = {
            "topicExists": False,
            "normalisedTopicIdentifier": normalised_topic_identifier,
            "normalisedTopicName": normalised_topic_name,
        }
    return jsonify(result)


@bp.route("/api/create-topic/<map_identifier>", methods=["POST"])
@login_required
def create_topic(map_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)

    if request.method == "POST":
        topic_identifier = request.form["topic-identifier"].strip()
        topic_name = request.form["topic-name"].strip()
        if not topic_name:
            topic_name = "Undefined"
        if topic_store.topic_exists(topic_map.identifier, topic_identifier):
            return jsonify({"status": "error", "code": 409}), 409
        else:
            topic = Topic(topic_identifier, "topic", topic_name)
            text_occurrence = Occurrence(
                instance_of="text",
                topic_identifier=topic.identifier,
                scope=UNIVERSAL_SCOPE,
                resource_data="Topic automatically created.",
            )
            timestamp = str(datetime.now())
            modification_attribute = Attribute(
                "modification-timestamp",
                timestamp,
                topic.identifier,
                data_type=DataType.TIMESTAMP,
            )

            # Persist objects to the topic store
            topic_store.set_topic(topic_map.identifier, topic)
            topic_store.set_occurrence(topic_map.identifier, text_occurrence)
            topic_store.set_attribute(topic_map.identifier, modification_attribute)

            return jsonify({"status": "success", "code": 201}), 201


@bp.route("/api/get-identifiers/<map_identifier>")
@login_required
def get_identifiers(map_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # TODO: Missing logic?

    query_term = request.args.get("q").lower()

    return jsonify(
        topic_store.get_topic_identifiers(map_identifier, query_term, limit=10)
    )


@bp.route("/api/get-network/<map_identifier>/<topic_identifier>")
def get_network(map_identifier, topic_identifier):
    topic_store = get_topic_store()

    if current_user.is_authenticated:  # User is logged in
        is_map_owner = topic_store.is_topic_map_owner(map_identifier, current_user.id)
        if is_map_owner:
            topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
        else:
            topic_map = topic_store.get_topic_map(map_identifier)
        if topic_map is None:
            abort(404)
    else:  # User is not logged in
        topic_map = topic_store.get_topic_map(map_identifier)
        if topic_map is None:
            abort(404)
        if (
            not topic_map.published
        ):  # User is not logged in and the map is not published
            abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier)

    scope_identifier = request.args.get("context", type=str)
    scope_filtered = request.args.get("filter", type=int)
    if not scope_filtered:
        scope_identifier = None

    def build_network(inner_identifier):
        base_name = tree[inner_identifier].payload["topic"].first_base_name.name
        instance_of = tree[inner_identifier].payload["topic"].instance_of
        level = tree[inner_identifier].payload["level"]
        children = tree[inner_identifier].children

        # group = instance_of
        color = f"#{level * 3}{level * 3}{level * 3}"
        if level == 0:
            color = "#A00"
        if inner_identifier == topic_identifier:
            color = "#F00"

        node = {
            "id": inner_identifier,
            "label": base_name + "\n[" + instance_of + "]",
            "instanceOf": instance_of,
            "color": color,
        }

        result[nodes].append(node)

        for child in children:
            # child_type_topic = topic_store.get_topic(map_identifier, child.type)
            edge = {
                "from": inner_identifier,
                "to": child.pointer,
                "font": {"align": "horizontal"},
                "color": {"color": "#666", "opacity": 0.5},
            }
            result[edges].append(edge)
            build_network(child.pointer)  # Recursive call

    if topic:
        tree = topic_store.get_topics_network(
            map_identifier, topic_identifier, scope=scope_identifier
        )
        if len(tree) > 1:
            nodes = 0
            edges = 1
            result = (
                [],
                [],
            )  # The result is a tuple containing two lists of dictionaries
            build_network(topic_identifier)
            return jsonify(result), 200
        else:
            return (
                jsonify({"status": "error", "code": 404, "message": "No network data"}),
                404,
            )
    else:
        return (
            jsonify({"status": "error", "code": 404, "message": "Topic not found"}),
            404,
        )
