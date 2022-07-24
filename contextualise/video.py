"""
video.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import maya
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from flask_security import login_required
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.collaborationmode import CollaborationMode
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint("video", __name__)


@bp.route("/videos/<map_identifier>/<topic_identifier>")
@login_required
def index(map_identifier, topic_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    video_occurrences = store.get_topic_occurrences(
        map_identifier,
        topic_identifier,
        "video",
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    videos = []
    for video_occurrence in video_occurrences:
        videos.append(
            {
                "identifier": video_occurrence.identifier,
                "title": video_occurrence.get_attribute_by_name("title").value,
                "scope": video_occurrence.scope,
                "url": video_occurrence.resource_ref,
            }
        )

    # occurrences_stats = store.get_topic_occurrences_statistics(map_identifier, topic_identifier)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "video/index.html",
        topic_map=topic_map,
        topic=topic,
        videos=videos,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/videos/add/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add(map_identifier, topic_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_video_title = request.form["video-title"].strip()
        form_video_url = request.form["video-url"].strip()
        form_video_scope = request.form["video-scope"].strip()

        # If no values have been provided set their default values
        if not form_video_scope:
            form_video_scope = session["current_scope"]

        # Validate form inputs
        if not form_video_title:
            error = error | 1
        if not form_video_url:
            error = error | 2
        if not store.topic_exists(topic_map.identifier, form_video_scope):
            error = error | 4

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            video_occurrence = Occurrence(
                instance_of="video",
                topic_identifier=topic.identifier,
                scope=form_video_scope,
                resource_ref=form_video_url,
            )
            title_attribute = Attribute(
                "title",
                form_video_title,
                video_occurrence.identifier,
                data_type=DataType.STRING,
            )

            # Persist objects to the topic store
            store.create_occurrence(topic_map.identifier, video_occurrence)
            store.create_attribute(topic_map.identifier, title_attribute)

            flash("Video link successfully added.", "success")
            return redirect(
                url_for(
                    "video.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

        return render_template(
            "video/add.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            video_title=form_video_title,
            video_url=form_video_url,
            video_scope=form_video_scope,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "video/add.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/videos/edit/<map_identifier>/<topic_identifier>/<video_identifier>",
    methods=("GET", "POST"),
)
@login_required
def edit(map_identifier, topic_identifier, video_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    video_occurrence = store.get_occurrence(
        map_identifier,
        video_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    form_video_title = video_occurrence.get_attribute_by_name("title").value
    form_video_scope = video_occurrence.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_video_title = request.form["video-title"].strip()
        form_video_scope = request.form["video-scope"].strip()

        # If no values have been provided set their default values
        if not form_video_scope:
            form_video_scope = session["current_scope"]

        # Validate form inputs
        if not form_video_title:
            error = error | 1
        if not store.topic_exists(topic_map.identifier, form_video_scope):
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            # Update video's title if it has changed
            if video_occurrence.get_attribute_by_name("title").value != form_video_title:
                store.update_attribute_value(
                    topic_map.identifier,
                    video_occurrence.get_attribute_by_name("title").identifier,
                    form_video_title,
                )

            # Update video's scope if it has changed
            if video_occurrence.scope != form_video_scope:
                store.update_occurrence_scope(map_identifier, video_occurrence.identifier, form_video_scope)

            flash("Video link successfully updated.", "success")
            return redirect(
                url_for(
                    "video.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    return render_template(
        "video/edit.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        video_identifier=video_occurrence.identifier,
        video_title=form_video_title,
        video_scope=form_video_scope,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/videos/delete/<map_identifier>/<topic_identifier>/<video_identifier>",
    methods=("GET", "POST"),
)
@login_required
def delete(map_identifier, topic_identifier, video_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    video_occurrence = store.get_occurrence(
        map_identifier,
        video_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    form_video_title = video_occurrence.get_attribute_by_name("title").value
    form_video_scope = video_occurrence.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    if request.method == "POST":
        # Delete video occurrence from topic store
        store.delete_occurrence(map_identifier, video_occurrence.identifier)

        flash("Video link successfully deleted.", "warning")
        return redirect(
            url_for(
                "video.index",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
            )
        )

    return render_template(
        "video/delete.html",
        topic_map=topic_map,
        topic=topic,
        video_identifier=video_occurrence.identifier,
        video_title=form_video_title,
        video_scope=form_video_scope,
        map_notes_count=map_notes_count,
    )
