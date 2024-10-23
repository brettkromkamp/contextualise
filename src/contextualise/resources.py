"""
resources.py file. Part of the Contextualise project.

October 22, 2024
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from itertools import groupby

from flask import Blueprint, render_template, request
from flask_login import current_user
from topicdb.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort

from contextualise import constants

from .topic_store import get_topic_store

bp = Blueprint("resources", __name__)


# regions Functions
def _initialize(map_identifier, topic_identifier, current_user):
    store = get_topic_store()

    collaboration_mode = None
    if current_user.is_authenticated:  # User is logged in
        is_map_owner = store.is_map_owner(map_identifier, current_user.id)
        if is_map_owner:
            topic_map = store.get_map(map_identifier, current_user.id)
        else:
            topic_map = store.get_map(map_identifier)
        if topic_map is None:
            abort(404)
        collaboration_mode = store.get_collaboration_mode(map_identifier, current_user.id)
        # The map is private and doesn't belong to the user who is trying to
        # access it
        if not topic_map.published and not is_map_owner:
            if not collaboration_mode:  # The user is not collaborating on the map
                abort(403)
    else:  # User is not logged in
        topic_map = store.get_map(map_identifier)
        if topic_map is None:
            abort(404)
        if not topic_map.published:  # User is not logged in and the map is not published
            abort(403)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    return store, topic_map, topic


# endregion


@bp.route("/resources/images/<map_identifier>/<topic_identifier>")
def images(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    # Pagination
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * constants.RESOURCE_ITEMS_PER_PAGE
    images_count = store.get_occurrences_count(map_identifier, "image")
    total_pages = (images_count + constants.RESOURCE_ITEMS_PER_PAGE - 1) // constants.RESOURCE_ITEMS_PER_PAGE

    image_occurrences = store.get_occurrences(
        map_identifier,
        instance_of="image",
        offset=offset,
        limit=constants.RESOURCE_ITEMS_PER_PAGE,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    images = []
    for image_occurrence in image_occurrences:
        images.append(
            {
                "topic_identifier": image_occurrence.topic_identifier,
                "identifier": image_occurrence.identifier,
                "title": image_occurrence.get_attribute_by_name("title").value,
                "scope": image_occurrence.scope,
                "url": image_occurrence.resource_ref,
            }
        )
    # Sort and group images by topic identifier
    sorted_images = sorted(images, key=lambda x: x["topic_identifier"])
    grouped_images = {k: list(v) for k, v in groupby(sorted_images, key=lambda x: x["topic_identifier"])}

    return render_template(
        "resources/images.html",
        topic_map=topic_map,
        topic=topic,
        images=grouped_images,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/resources/files/<map_identifier>/<topic_identifier>")
def files(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)


@bp.route("/resources/videos/<map_identifier>/<topic_identifier>")
def videos(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)


@bp.route("/resources/links/<map_identifier>/<topic_identifier>")
def links(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)


@bp.route("/resources/scenes/<map_identifier>/<topic_identifier>")
def scenes(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)
