"""
resources.py file. Part of the Contextualise project.

October 22, 2024
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from itertools import groupby

import maya
from flask import Blueprint, render_template, request
from flask_login import current_user
from topicdb.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort

from contextualise import constants
from contextualise.temporaltype import TemporalType

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

    image_occurrences = store.get_occurrences(
        map_identifier,
        instance_of="image",
        offset=offset,
        limit=constants.RESOURCE_ITEMS_PER_PAGE,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    images_count = len(image_occurrences)
    total_pages = (images_count + constants.RESOURCE_ITEMS_PER_PAGE - 1) // constants.RESOURCE_ITEMS_PER_PAGE

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

    # Pagination
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * constants.RESOURCE_ITEMS_PER_PAGE

    file_occurrences = store.get_occurrences(
        map_identifier,
        instance_of="file",
        offset=offset,
        limit=constants.RESOURCE_ITEMS_PER_PAGE,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    files_count = len(file_occurrences)
    total_pages = (files_count + constants.RESOURCE_ITEMS_PER_PAGE - 1) // constants.RESOURCE_ITEMS_PER_PAGE

    files = []
    for file_occurrence in file_occurrences:
        files.append(
            {
                "topic_identifier": file_occurrence.topic_identifier,
                "identifier": file_occurrence.identifier,
                "title": file_occurrence.get_attribute_by_name("title").value,
                "scope": file_occurrence.scope,
                "url": file_occurrence.resource_ref,
            }
        )
    # Sort and group files by topic identifier
    sorted_files = sorted(files, key=lambda x: x["topic_identifier"])
    grouped_files = {k: list(v) for k, v in groupby(sorted_files, key=lambda x: x["topic_identifier"])}

    return render_template(
        "resources/files.html",
        topic_map=topic_map,
        topic=topic,
        files=grouped_files,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/resources/videos/<map_identifier>/<topic_identifier>")
def videos(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    # Pagination
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * constants.RESOURCE_ITEMS_PER_PAGE

    video_occurrences = store.get_occurrences(
        map_identifier,
        instance_of="video",
        offset=offset,
        limit=constants.RESOURCE_ITEMS_PER_PAGE,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    videos_count = len(video_occurrences)
    total_pages = (videos_count + constants.RESOURCE_ITEMS_PER_PAGE - 1) // constants.RESOURCE_ITEMS_PER_PAGE

    videos = []
    for video_occurrence in video_occurrences:
        videos.append(
            {
                "topic_identifier": video_occurrence.topic_identifier,
                "identifier": video_occurrence.identifier,
                "title": video_occurrence.get_attribute_by_name("title").value,
                "scope": video_occurrence.scope,
                "url": video_occurrence.resource_ref,
            }
        )
    # Sort and group videos by topic identifier
    sorted_videos = sorted(videos, key=lambda x: x["topic_identifier"])
    grouped_videos = {k: list(v) for k, v in groupby(sorted_videos, key=lambda x: x["topic_identifier"])}

    return render_template(
        "resources/videos.html",
        topic_map=topic_map,
        topic=topic,
        videos=grouped_videos,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/resources/links/<map_identifier>/<topic_identifier>")
def links(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    # Pagination
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * constants.RESOURCE_ITEMS_PER_PAGE

    link_occurrences = store.get_occurrences(
        map_identifier,
        instance_of="url",
        offset=offset,
        limit=constants.RESOURCE_ITEMS_PER_PAGE,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    links_count = len(link_occurrences)
    total_pages = (links_count + constants.RESOURCE_ITEMS_PER_PAGE - 1) // constants.RESOURCE_ITEMS_PER_PAGE

    links = []
    for link_occurrence in link_occurrences:
        links.append(
            {
                "topic_identifier": link_occurrence.topic_identifier,
                "identifier": link_occurrence.identifier,
                "title": link_occurrence.get_attribute_by_name("title").value,
                "scope": link_occurrence.scope,
                "url": link_occurrence.resource_ref,
            }
        )
    # Sort and group links by topic identifier
    sorted_links = sorted(links, key=lambda x: x["topic_identifier"])
    grouped_links = {k: list(v) for k, v in groupby(sorted_links, key=lambda x: x["topic_identifier"])}

    return render_template(
        "resources/links.html",
        topic_map=topic_map,
        topic=topic,
        links=grouped_links,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/resources/scenes/<map_identifier>/<topic_identifier>")
def scenes(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    # Pagination
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * constants.RESOURCE_ITEMS_PER_PAGE

    file_occurrences = store.get_occurrences(
        map_identifier,
        instance_of="3d-scene",
        offset=offset,
        limit=constants.RESOURCE_ITEMS_PER_PAGE,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    files_count = len(file_occurrences)
    total_pages = (files_count + constants.RESOURCE_ITEMS_PER_PAGE - 1) // constants.RESOURCE_ITEMS_PER_PAGE

    files = []
    for file_occurrence in file_occurrences:
        files.append(
            {
                "topic_identifier": file_occurrence.topic_identifier,
                "identifier": file_occurrence.identifier,
                "title": file_occurrence.get_attribute_by_name("title").value,
                "scope": file_occurrence.scope,
                "url": file_occurrence.resource_ref,
            }
        )
    # Sort and group (3D) scene files by topic identifier
    sorted_files = sorted(files, key=lambda x: x["topic_identifier"])
    grouped_files = {k: list(v) for k, v in groupby(sorted_files, key=lambda x: x["topic_identifier"])}

    return render_template(
        "resources/scenes.html",
        topic_map=topic_map,
        topic=topic,
        files=grouped_files,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/resources/notes/<map_identifier>/<topic_identifier>")
def notes(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    # Pagination
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * constants.RESOURCE_ITEMS_PER_PAGE

    note_occurrences = store.get_occurrences(
        map_identifier,
        instance_of="note",
        offset=offset,
        limit=constants.RESOURCE_ITEMS_PER_PAGE,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    notes_count = len(note_occurrences)
    total_pages = (notes_count + constants.RESOURCE_ITEMS_PER_PAGE - 1) // constants.RESOURCE_ITEMS_PER_PAGE

    notes = []
    for note_occurrence in note_occurrences:
        notes.append(
            {
                "topic_identifier": note_occurrence.topic_identifier,
                "identifier": note_occurrence.identifier,
                "title": note_occurrence.get_attribute_by_name("title").value,
                "scope": note_occurrence.scope,
                "url": note_occurrence.resource_ref,
            }
        )
    # Sort and group notes by topic identifier, but exclude the "notes" topic
    sorted_notes = sorted(notes, key=lambda x: x["topic_identifier"])
    grouped_notes = {k: list(v) for k, v in groupby(sorted_notes, key=lambda x: x["topic_identifier"]) if k != "notes"}

    return render_template(
        "resources/notes.html",
        topic_map=topic_map,
        topic=topic,
        notes=grouped_notes,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/resources/temporals/<map_identifier>/<topic_identifier>")
def temporals(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    # Pagination
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * constants.RESOURCE_ITEMS_PER_PAGE

    temporal_occurrences = store.get_occurrences(
        map_identifier,
        instance_of="temporal-event",
        offset=offset,
        limit=constants.RESOURCE_ITEMS_PER_PAGE,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    ) + store.get_occurrences(
        map_identifier,
        instance_of="temporal-era",
        offset=offset,
        limit=constants.RESOURCE_ITEMS_PER_PAGE,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    temporals_count = len(temporal_occurrences)
    total_pages = (temporals_count + constants.RESOURCE_ITEMS_PER_PAGE - 1) // constants.RESOURCE_ITEMS_PER_PAGE

    temporals = []
    for temporal_occurrence in temporal_occurrences:
        temporal_type = TemporalType.ERA if temporal_occurrence.instance_of == "temporal-era" else TemporalType.EVENT
        temporal_end_date = (
            temporal_occurrence.get_attribute_by_name("temporal-end-date").value
            if temporal_type is TemporalType.ERA
            else None
        )
        temporal_end_date_view = ""
        if temporal_end_date:
            temporal_end_date_view = maya.parse(temporal_end_date).date.strftime("%a, %d %b %Y")
        temporals.append(
            {
                "topic_identifier": temporal_occurrence.topic_identifier,
                "identifier": temporal_occurrence.identifier,
                "type": temporal_type.name.lower(),
                "start_date": temporal_occurrence.get_attribute_by_name("temporal-start-date").value,
                "start_date_view": maya.parse(temporal_occurrence.get_attribute_by_name("temporal-start-date").value).date.strftime("%a, %d %b %Y"),
                "end_date": temporal_end_date,
                "end_date_view": temporal_end_date_view,
                "description": temporal_occurrence.resource_data.decode("utf-8")
                if temporal_occurrence.has_data
                else None,
                "scope": temporal_occurrence.scope,
            }
        )
    # Sort temporals chronologically (by start date)
    sorted_temporals = sorted(temporals, key=lambda x: x["start_date"])

    return render_template(
        "resources/temporals.html",
        topic_map=topic_map,
        topic=topic,
        temporals=sorted_temporals,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/resources/locations/<map_identifier>/<topic_identifier>")
def locations(map_identifier, topic_identifier):
    store, topic_map, topic = _initialize(map_identifier, topic_identifier, current_user)

    # Pagination
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * constants.RESOURCE_ITEMS_PER_PAGE

    location_occurrences = store.get_occurrences(
        map_identifier,
        instance_of="location",
        offset=offset,
        limit=constants.RESOURCE_ITEMS_PER_PAGE,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    locations_count = len(location_occurrences)
    total_pages = (locations_count + constants.RESOURCE_ITEMS_PER_PAGE - 1) // constants.RESOURCE_ITEMS_PER_PAGE

    locations = []
    for location_occurrence in location_occurrences:
        locations.append(
            {
                "topic_identifier": location_occurrence.topic_identifier,
                "identifier": location_occurrence.identifier,
                "name": location_occurrence.get_attribute_by_name("location-name").value,
                "description": location_occurrence.resource_data.decode("utf-8") if location_occurrence.has_data
                else None,
                "coordinates": location_occurrence.get_attribute_by_name("geographic-coordinates").value,
                "scope": location_occurrence.scope,
            }
        )
    # Sort locations by topic identifier
    sorted_locations = sorted(locations, key=lambda x: x["topic_identifier"])

    return render_template(
        "resources/locations.html",
        topic_map=topic_map,
        topic=topic,
        locations=sorted_locations,
        page=page,
        total_pages=total_pages,
    )
