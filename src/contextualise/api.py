"""
api.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from datetime import datetime

import mistune
from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required  # type: ignore
from slugify import slugify
from topicdb.models.association import Association
from topicdb.models.attribute import Attribute
from topicdb.models.datatype import DataType
from topicdb.models.occurrence import Occurrence
from topicdb.models.topic import Topic
from topicdb.store.retrievalmode import RetrievalMode

from contextualise.temporaltype import TemporalType

from . import constants
from .topic_store import get_topic_store
from .utilities.highlight_renderer import HighlightRenderer

bp = Blueprint("api", __name__)


# region Functions
def _initialize(map_identifier, topic_identifier, current_user):
    store = get_topic_store()

    is_map_owner = False
    if current_user.is_authenticated:  # User is logged in
        is_map_owner = store.is_map_owner(map_identifier, current_user.id)
        if is_map_owner:
            topic_map = store.get_map(map_identifier, current_user.id)
        else:
            topic_map = store.get_map(map_identifier)
    else:  # User is not logged in
        topic_map = store.get_map(map_identifier)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    return store, topic_map, topic


# endregion


# region JSON API
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
                scope=constants.UNIVERSAL_SCOPE,  # TODO: Should it be session["current_scope"]?
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
        edges_count = store.get_topic_associations_count(map_identifier, inner_identifier)

        # group = instance_of
        color = f"#{level * 3}{level * 3}{level * 3}"
        if level == 0:
            color = "#A00"
        if inner_identifier == topic_identifier:
            color = "#F00"

        node = {
            "id": inner_identifier,
            # "label": base_name + "\n[" + instance_of + "]",
            "label": base_name,
            "instanceOf": instance_of,
            "value": edges_count,
            "color": color,
        }

        result[nodes].append(node)

        for child in children:
            # child_type_topic = store.get_topic(map_identifier, child.type)
            edge = {
                "from": inner_identifier,
                "to": child.pointer,
                "label": child.type,
                "font": {"align": "middle"},
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


@bp.route("/api/get-timeline/<map_identifier>")
def get_timeline(map_identifier):
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

    scope_identifier = request.args.get("scope", type=str)
    scope_filtered = request.args.get("filter", type=int)
    if not scope_filtered:
        scope_identifier = None

    events = store.get_occurrences(
        map_identifier=map_identifier,
        instance_of="temporal-event",
        scope=scope_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    eras = store.get_occurrences(
        map_identifier=map_identifier,
        instance_of="temporal-era",
        scope=scope_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    temporal_events = []
    for event in events:
        text = event.resource_data.decode() if event.resource_data else "No description provided."
        start_year, start_month, start_day = event.get_attribute_by_name("temporal-start-date").value.split("-")
        media_url = (
            event.get_attribute_by_name("temporal-media-url").value
            if event.get_attribute_by_name("temporal-media-url")
            else "/static/no-data.svg"
        )
        event_topic = store.get_topic(map_identifier, event.topic_identifier, scope=scope_identifier)
        text += f"""
        <br />
        <br />
        <a target="_self" href="/temporals/{map_identifier}/{event_topic.identifier}"><small>Go to temporal</small></a>
        """.strip()
        temporal_events.append(
            {
                "start_date": {
                    "year": start_year,
                    "month": start_month,
                    "day": start_day,
                },
                "text": {
                    "headline": f'<a target="_self" href="/topics/view/{map_identifier}/{event_topic.identifier}">{event_topic.first_base_name.name}</a>',
                    "text": text,
                },
                "unique_id": event.topic_identifier,
                "media": {
                    "url": media_url,
                },
            }
        )
    temporal_eras = []
    for era in eras:
        text = era.resource_data.decode() if era.resource_data else "No description provided."
        start_year, start_month, start_day = era.get_attribute_by_name("temporal-start-date").value.split("-")
        end_year, end_month, end_day = era.get_attribute_by_name("temporal-end-date").value.split("-")
        era_topic = store.get_topic(map_identifier, era.topic_identifier, scope=scope_identifier)
        temporal_eras.append(
            {
                "start_date": {
                    "year": start_year,
                    "month": start_month,
                    "day": start_day,
                },
                "end_date": {
                    "year": end_year,
                    "month": end_month,
                    "day": end_day,
                },
                "text": {
                    "headline": era_topic.first_base_name.name,
                    "text": text,
                },
            }
        )

    if len(temporal_events) == 0:
        return (
            jsonify({"status": "error", "code": 404, "message": "No temporal data"}),
            404,
        )

    result = {
        "scale": "human",
        "events": temporal_events,
        "eras": temporal_eras,
    }
    return jsonify(result), 200


@bp.route("/api/get-geographic-map/<map_identifier>")
def get_geographic_map(map_identifier):
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

    scope_identifier = request.args.get("scope", type=str)
    scope_filtered = request.args.get("filter", type=int)
    if not scope_filtered:
        scope_identifier = None

    location_occurrences = store.get_occurrences(
        map_identifier=map_identifier,
        instance_of="location",
        scope=scope_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if len(location_occurrences) == 0:
        return (
            jsonify({"status": "error", "code": 404, "message": "No geographic data"}),
            404,
        )

    locations = []
    for location_occurrence in location_occurrences:
        latitude, longitude = location_occurrence.get_attribute_by_name("geographic-coordinates").value.split(",")
        description = location_occurrence.resource_data.decode() if location_occurrence.resource_data else ""
        location_topic = store.get_topic(map_identifier, location_occurrence.topic_identifier, scope=scope_identifier)
        locations.append(
            {
                "map_identifier": map_identifier,
                "occurrence_identifier": location_occurrence.identifier,
                "topic_identifier": location_occurrence.topic_identifier,
                "base_name": location_topic.first_base_name.name,
                "description": description,
                "lat": latitude,
                "lng": longitude,
                "label": location_occurrence.get_attribute_by_name("location-name").value,
            }
        )

    result = {
        "locations": locations,
    }
    return jsonify(result), 200


@bp.route("/api/create-association/<map_identifier>", methods=("POST",))
@login_required
def create_association(map_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        return jsonify({"status": "error", "code": 404}), 404

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
        association_scope = constants.UNIVERSAL_SCOPE
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


# endregion


# region HTML (HTMX) API
# htmx-specific (https://htmx.org/docs/) endpoints that return HTML partials


@bp.route("/api/get-associations/<map_identifier>/<topic_identifier>/<scope_identifier>/<int:scope_filtered>")
def get_associations(map_identifier, topic_identifier, scope_identifier, scope_filtered):
    store, topic_map, _ = _initialize(map_identifier, topic_identifier, current_user)

    if scope_filtered:
        topic_associations = store.get_topic_associations(map_identifier, topic_identifier, scope=scope_identifier)
    else:
        topic_associations = store.get_topic_associations(map_identifier, topic_identifier)

    # Filter-out associations of type 'navigation' (knowledge path) and 'categorization' (tags)
    filtered_associations = [
        topic_association
        for topic_association in topic_associations
        if topic_association.instance_of not in ("navigation", "categorization")
    ]
    if filtered_associations:
        associations = store.get_association_groups(
            map_identifier, topic_identifier, associations=filtered_associations
        )
    else:
        associations = []

    return render_template(
        "api/association/get_associations.html",
        topic_map=topic_map,
        topic_identifier=topic_identifier,
        scope_identifier=scope_identifier,
        associations=associations,
    )


@bp.route("/api/change-scope/<map_identifier>/<topic_identifier>")
@login_required
def change_scope(map_identifier, topic_identifier):
    _, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    return render_template(
        "api/topic/change_scope.html",
        topic_map=topic_map,
        topic=topic,
    )


@bp.route("/api/delete-map/<map_identifier>")
@login_required
def delete_map(map_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)

    return render_template("api/map/delete.html", topic_map=topic_map)


@bp.route("/api/delete-topic/<map_identifier>/<topic_identifier>")
@login_required
def delete_topic(map_identifier, topic_identifier):
    _, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    delete_topic_identifier = topic.identifier
    delete_topic_name = topic.first_base_name.name
    delete_topic_instance_of = topic.instance_of

    return render_template(
        "api/topic/delete.html",
        topic_map=topic_map,
        delete_topic_identifier=delete_topic_identifier,
        delete_topic_name=delete_topic_name,
        delete_topic_instance_of=delete_topic_instance_of,
    )


@bp.route("/api/delete-topic-note/<map_identifier>/<topic_identifier>/<note_identifier>")
@login_required
def delete_topic_note(map_identifier, topic_identifier, note_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    note_occurrence = store.get_occurrence(
        map_identifier,
        note_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    delete_note_identifier = note_identifier
    delete_note_title = note_occurrence.get_attribute_by_name("title").value
    markdown = mistune.create_markdown(
        renderer=HighlightRenderer(escape=False),
        plugins=[
            "strikethrough",
            "footnotes",
            "table",
        ],
    )
    delete_note_text = markdown(note_occurrence.resource_data.decode())
    delete_note_scope = note_occurrence.scope

    return render_template(
        "api/topic/delete_note.html",
        topic_map=topic_map,
        topic=topic,
        delete_note_identifier=delete_note_identifier,
        delete_note_title=delete_note_title,
        delete_note_text=delete_note_text,
        delete_note_scope=delete_note_scope,
    )


@bp.route("/api/delete-notes-note/<map_identifier>/<topic_identifier>/<note_identifier>")
@login_required
def delete_notes_note(map_identifier, topic_identifier, note_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    note_occurrence = store.get_occurrence(
        map_identifier,
        note_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    delete_note_identifier = note_identifier
    delete_note_title = note_occurrence.get_attribute_by_name("title").value
    markdown = mistune.create_markdown(
        renderer=HighlightRenderer(escape=False),
        plugins=[
            "strikethrough",
            "footnotes",
            "table",
        ],
    )
    delete_note_text = markdown(note_occurrence.resource_data.decode())
    delete_note_scope = note_occurrence.scope

    return render_template(
        "api/note/delete.html",
        topic_map=topic_map,
        topic=topic,
        delete_note_identifier=delete_note_identifier,
        delete_note_title=delete_note_title,
        delete_note_text=delete_note_text,
        delete_note_scope=delete_note_scope,
    )


@bp.route("/api/delete-link/<map_identifier>/<topic_identifier>/<link_identifier>")
@login_required
def delete_link(map_identifier, topic_identifier, link_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    link_occurrence = store.get_occurrence(
        map_identifier,
        link_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    delete_link_identifier = link_identifier
    delete_link_title = link_occurrence.get_attribute_by_name("title").value
    delete_link_url = link_occurrence.resource_ref
    delete_link_scope = link_occurrence.scope

    return render_template(
        "api/link/delete.html",
        topic_map=topic_map,
        topic=topic,
        delete_link_identifier=delete_link_identifier,
        delete_link_title=delete_link_title,
        delete_link_url=delete_link_url,
        delete_link_scope=delete_link_scope,
    )


@bp.route("/api/delete-video/<map_identifier>/<topic_identifier>/<video_identifier>")
@login_required
def delete_video(map_identifier, topic_identifier, video_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    video_occurrence = store.get_occurrence(
        map_identifier,
        video_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    delete_video_identifier = video_identifier
    delete_video_title = video_occurrence.get_attribute_by_name("title").value
    delete_video_url = video_occurrence.resource_ref
    delete_video_scope = video_occurrence.scope

    return render_template(
        "api/video/delete.html",
        topic_map=topic_map,
        topic=topic,
        delete_video_identifier=delete_video_identifier,
        delete_video_title=delete_video_title,
        delete_video_url=delete_video_url,
        delete_video_scope=delete_video_scope,
    )


@bp.route("/api/delete-image/<map_identifier>/<topic_identifier>/<image_identifier>")
@login_required
def delete_image(map_identifier, topic_identifier, image_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    image_occurrence = store.get_occurrence(
        map_identifier,
        image_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    delete_image_identifier = image_identifier
    delete_image_title = image_occurrence.get_attribute_by_name("title").value
    delete_image_resource_ref = image_occurrence.resource_ref
    delete_image_scope = image_occurrence.scope

    return render_template(
        "api/image/delete.html",
        topic_map=topic_map,
        topic=topic,
        delete_image_identifier=delete_image_identifier,
        delete_image_title=delete_image_title,
        delete_image_resource_ref=delete_image_resource_ref,
        delete_image_scope=delete_image_scope,
    )


@bp.route("/api/delete-file/<map_identifier>/<topic_identifier>/<file_identifier>")
@login_required
def delete_file(map_identifier, topic_identifier, file_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    file_occurrence = store.get_occurrence(
        map_identifier,
        file_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    delete_file_identifier = file_identifier
    delete_file_title = file_occurrence.get_attribute_by_name("title").value
    delete_file_scope = file_occurrence.scope

    return render_template(
        "api/file/delete.html",
        topic_map=topic_map,
        topic=topic,
        delete_file_identifier=delete_file_identifier,
        delete_file_title=delete_file_title,
        delete_file_scope=delete_file_scope,
    )


@bp.route("/api/delete-scene/<map_identifier>/<topic_identifier>/<file_identifier>")
@login_required
def delete_scene(map_identifier, topic_identifier, file_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    file_occurrence = store.get_occurrence(
        map_identifier,
        file_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    delete_file_identifier = file_identifier
    delete_file_title = file_occurrence.get_attribute_by_name("title").value
    delete_file_scope = file_occurrence.scope

    return render_template(
        "api/three_d/delete.html",
        topic_map=topic_map,
        topic=topic,
        delete_file_identifier=delete_file_identifier,
        delete_file_title=delete_file_title,
        delete_file_scope=delete_file_scope,
    )


@bp.route("/api/delete-temporal/<map_identifier>/<topic_identifier>/<temporal_identifier>")
@login_required
def delete_temporal(map_identifier, topic_identifier, temporal_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    temporal_occurrence = store.get_occurrence(
        map_identifier,
        temporal_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    delete_temporal_identifier = temporal_identifier
    delete_temporal_type = (
        TemporalType.EVENT if temporal_occurrence.instance_of == "temporal-event" else TemporalType.ERA
    )
    delete_temporal_description = (
        temporal_occurrence.resource_data.decode("utf-8") if temporal_occurrence.has_data else None
    )
    delete_temporal_start_date = temporal_occurrence.get_attribute_by_name("temporal-start-date").value
    delete_temporal_end_date = (
        temporal_occurrence.get_attribute_by_name("temporal-end-date").value
        if delete_temporal_type is TemporalType.ERA
        else None
    )
    delete_temporal_scope = temporal_occurrence.scope

    return render_template(
        "api/temporal/delete.html",
        topic_map=topic_map,
        topic=topic,
        delete_temporal_identifier=delete_temporal_identifier,
        delete_temporal_type=delete_temporal_type.name.lower(),
        delete_temporal_description=delete_temporal_description,
        delete_temporal_start_date=delete_temporal_start_date,
        delete_temporal_end_date=delete_temporal_end_date,
        delete_temporal_scope=delete_temporal_scope,
    )


@bp.route("/api/delete-location/<map_identifier>/<topic_identifier>/<location_identifier>")
@login_required
def delete_location(map_identifier, topic_identifier, location_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    location_occurrence = store.get_occurrence(
        map_identifier,
        location_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    delete_location_identifier = location_identifier
    delete_topic_identifier = location_occurrence.topic_identifier
    delete_location_name = location_occurrence.get_attribute_by_name("location-name").value
    delete_location_description = (
        location_occurrence.resource_data.decode("utf-8") if location_occurrence.has_data else None
    )
    delete_location_scope = location_occurrence.scope

    return render_template(
        "api/location/delete.html",
        topic_map=topic_map,
        topic=topic,
        delete_location_identifier=delete_location_identifier,
        delete_topic_identifier=delete_topic_identifier,
        delete_location_name=delete_location_name,
        delete_location_description=delete_location_description,
        delete_location_scope=delete_location_scope,
    )


@bp.route("/api/delete-name/<map_identifier>/<topic_identifier>/<name_identifier>")
@login_required
def delete_name(map_identifier, topic_identifier, name_identifier):
    _, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    delete_name_identifier = name_identifier
    delete_topic_name = topic.get_base_name(name_identifier).name
    delete_topic_name_scope = topic.get_base_name(name_identifier).scope

    return render_template(
        "api/topic/delete_name.html",
        topic_map=topic_map,
        topic=topic,
        delete_name_identifier=delete_name_identifier,
        delete_topic_name=delete_topic_name,
        delete_topic_name_scope=delete_topic_name_scope,
    )


@bp.route("/api/delete-association/<map_identifier>/<topic_identifier>/<association_identifier>")
@login_required
def delete_association(map_identifier, topic_identifier, association_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    association = store.get_association(map_identifier, association_identifier)

    return render_template(
        "api/association/delete.html",
        topic_map=topic_map,
        topic=topic,
        association=association,
    )


# endregion
