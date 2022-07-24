"""
api.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import os
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_security import current_user, login_required
from slugify import slugify
from topicdb.core.models.association import Association
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.models.topic import Topic

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
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        return jsonify({"status": "error", "code": 404}), 404

    normalised_topic_identifier = slugify(str(request.args.get("q").lower()))
    normalised_topic_name = " ".join([word.capitalize() for word in normalised_topic_identifier.split("-")])
    exists = store.topic_exists(map_identifier, normalised_topic_identifier)
    if exists:
        result = {"topicExists": True}
    else:
        result = {
            "topicExists": False,
            "normalisedTopicIdentifier": normalised_topic_identifier,
            "normalisedTopicName": normalised_topic_name,
        }
    return jsonify(result), 200


@bp.route("/api/create-topic/<map_identifier>", methods=["POST"])
@login_required
def create_topic(map_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        return jsonify({"status": "error", "code": 404}), 404

    if request.method == "POST":
        topic_identifier = request.form["topic-identifier"].strip()
        topic_name = request.form["topic-name"].strip()
        if not topic_name:
            topic_name = "Undefined"
        if store.topic_exists(topic_map.identifier, topic_identifier):
            return jsonify({"status": "error", "code": 409}), 409
        else:
            topic = Topic(topic_identifier, "topic", topic_name)
            text_occurrence = Occurrence(
                instance_of="text",
                topic_identifier=topic.identifier,
                scope=UNIVERSAL_SCOPE,  # TODO: Should it be session["current_scope"]?
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
            store.create_topic(topic_map.identifier, topic)
            store.create_occurrence(topic_map.identifier, text_occurrence)
            store.create_attribute(topic_map.identifier, modification_attribute)

            return jsonify({"status": "success", "code": 201}), 201


@bp.route("/api/get-identifiers/<map_identifier>")
@login_required
def get_identifiers(map_identifier):
    result = []
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        return jsonify({"status": "error", "code": 404}), 404
    # TODO: Missing logic?

    query_term = request.args.get("q").lower()
    instance_of = request.args.get("instance-of")
    if instance_of:
        result = store.get_topic_identifiers(map_identifier, query_term, instance_ofs=[instance_of.lower()], limit=10)
    else:
        result = store.get_topic_identifiers(map_identifier, query_term, limit=10)
    return jsonify(result), 200


# Custom endpoint to integrate with https://github.com/amsify42/jquery.amsify.suggestags
@bp.route("/api/get-tags/<map_identifier>")
@login_required
def get_tags(map_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        return jsonify({"status": "error", "code": 404}), 404
    # TODO: Missing logic?

    query_term = request.args.get("term").lower()
    result = {"suggestions": store.get_topic_identifiers(map_identifier, query_term, instance_ofs=["tag"], limit=10)}
    return jsonify(result), 200


@bp.route("/api/get-network/<map_identifier>/<topic_identifier>")
def get_network(map_identifier, topic_identifier):
    store = get_topic_store()

    if current_user.is_authenticated:  # User is logged in
        is_map_owner = store.is_map_owner(map_identifier, current_user.id)
        if is_map_owner:
            topic_map = store.get_map(map_identifier, current_user.id)
        else:
            topic_map = store.get_map(map_identifier)
        if topic_map is None:
            return jsonify({"status": "error", "code": 404}), 404
    else:  # User is not logged in
        topic_map = store.get_map(map_identifier)
        if topic_map is None:
            return jsonify({"status": "error", "code": 404}), 404
        if not topic_map.published:  # User is not logged in and the map is not published
            return jsonify({"status": "error", "code": 403}), 403

    topic = store.get_topic(map_identifier, topic_identifier)

    scope_identifier = request.args.get("scope", type=str)
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
            # child_type_topic = store.get_topic(map_identifier, child.type)
            edge = {
                "from": inner_identifier,
                "to": child.pointer,
                "label": child.type,
                "font": {"align": "horizontal"},
                # "arrows": "to, from",
                "color": {"color": "#666", "opacity": 0.5},
            }
            result[edges].append(edge)
            build_network(child.pointer)  # Recursive call

    if topic:
        tree = store.get_topics_network(map_identifier, topic_identifier, scope=scope_identifier)
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


@bp.route("/api/get-association-groups/<map_identifier>/<topic_identifier>/<scope_identifier>/<int:scope_filtered>")
def get_association_groups(map_identifier, topic_identifier, scope_identifier, scope_filtered):
    store = get_topic_store()

    if current_user.is_authenticated:  # User is logged in
        is_map_owner = store.is_map_owner(map_identifier, current_user.id)
        if is_map_owner:
            topic_map = store.get_map(map_identifier, current_user.id)
        else:
            topic_map = store.get_map(map_identifier)
        if topic_map is None:
            return jsonify({"status": "error", "code": 404}), 404
    else:  # User is not logged in
        topic_map = store.get_map(map_identifier)
        if topic_map is None:
            return jsonify({"status": "error", "code": 404}), 404

    if scope_filtered:
        associations = store.get_association_groups(map_identifier, topic_identifier, scope=scope_identifier)
    else:
        associations = store.get_association_groups(map_identifier, topic_identifier)
    if not associations:
        return jsonify({"status": "error", "code": 404}), 404

    result = []
    for instance_of, roles in associations.dict.items():
        result_roles = []
        for role, topic_refs in roles.items():
            result_topic_refs = []
            for topic_ref in topic_refs:
                topic_ref_topic = store.get_topic(map_identifier, topic_ref)
                result_topic_refs.append(
                    {
                        "identifier": topic_ref,
                        "name": topic_ref_topic.first_base_name.name,
                    }
                )
            else:
                role_topic = store.get_topic(map_identifier, role)
                result_roles.append(
                    {
                        "identifier": role,
                        "name": role_topic.first_base_name.name,
                        "topicRefs": result_topic_refs,
                    }
                )
        else:
            instance_of_topic = store.get_topic(map_identifier, instance_of)
            result.append(
                {
                    "identifier": instance_of,
                    "name": instance_of_topic.first_base_name.name,
                    "roles": result_roles,
                }
            )

    return jsonify(result), 200


@bp.route("/api/create-association/<map_identifier>", methods=["POST"])
@login_required
def create_association(map_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        return jsonify({"status": "error", "code": 404}), 404

    if request.method == "POST":
        association_dest_topic_ref = request.form["association-dest-topic-ref"].strip()
        association_dest_role_spec = request.form["association-dest-role-spec"].strip()
        association_src_topic_ref = request.form["association-src-topic-ref"].strip()
        association_src_role_spec = request.form["association-src-role-spec"].strip()
        association_instance_of = request.form["association-instance-of"].strip()
        association_scope = request.form["association-scope"].strip()
        association_name = request.form["association-name"].strip()
        association_identifier = request.form["association-identifier"].strip()

        if not store.topic_exists(topic_map.identifier, association_dest_topic_ref):
            return jsonify({"status": "error", "code": 409}), 409
        if not store.topic_exists(topic_map.identifier, association_src_topic_ref):
            return jsonify({"status": "error", "code": 409}), 409

        # If no values have been provided set their default values
        if not association_dest_role_spec:
            association_dest_role_spec = "related"
        if not association_src_role_spec:
            association_src_role_spec = "related"
        if not association_instance_of:
            association_instance_of = "association"
        if not association_scope:
            association_scope = UNIVERSAL_SCOPE
        if not association_name:
            association_name = "Undefined"
        if not association_identifier:
            association_identifier = ""

        association = Association(
            identifier=association_identifier,
            instance_of=association_instance_of,
            name=association_name,
            scope=association_scope,
            src_topic_ref=association_src_topic_ref,
            dest_topic_ref=association_dest_topic_ref,
            src_role_spec=association_src_role_spec,
            dest_role_spec=association_dest_role_spec,
        )

        # Persist association object to the topic store
        store.create_association(map_identifier, association)

    return jsonify({"status": "success", "code": 201}), 201
