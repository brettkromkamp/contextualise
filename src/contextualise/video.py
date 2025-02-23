"""
video.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import maya  # type: ignore
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required  # type: ignore
from topicdb.models.attribute import Attribute
from topicdb.models.datatype import DataType
from topicdb.models.occurrence import Occurrence
from topicdb.store.retrievalmode import RetrievalMode
from topicdb.topicdberror import TopicDbError

from contextualise.utilities.topicstore import initialize

bp = Blueprint("video", __name__)


@bp.route("/videos/<map_identifier>/<topic_identifier>")
@login_required
def index(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

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
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_video_title = request.form.get("video-title", "").strip()
        form_video_url = request.form.get("video-url", "").strip()
        form_video_scope = request.form.get("video-scope", "").strip()

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
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
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


@bp.route("/videos/edit/<map_identifier>/<topic_identifier>/<video_identifier>", methods=("GET", "POST"))
@login_required
def edit(map_identifier, topic_identifier, video_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

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
        form_video_title = request.form.get("video-title", "").strip()
        form_video_scope = request.form.get("video-scope", "").strip()

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
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
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


@bp.route("/videos/delete/<map_identifier>/<topic_identifier>/<video_identifier>", methods=("POST",))
@login_required
def delete(map_identifier, topic_identifier, video_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    error = 0

    video_occurrence = store.get_occurrence(
        map_identifier,
        video_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if not video_occurrence:
        error = error | 1

    if error != 0:
        flash("An error occurred while trying to delete the link.", "warning")
    else:
        try:
            # Delete video occurrence from topic store
            store.delete_occurrence(map_identifier, video_occurrence.identifier)
            flash("Video link successfully deleted.", "success")
        except TopicDbError:
            flash(
                "An error occurred while trying to delete the video link. The link was not deleted.",
                "warning",
            )
    return redirect(
        url_for(
            "video.index",
            map_identifier=topic_map.identifier,
            topic_identifier=topic.identifier,
        )
    )
