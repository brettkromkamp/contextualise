"""
attribute.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import os
import uuid

import maya
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from flask_security import login_required
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.collaborationmode import CollaborationMode
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint("file", __name__)

RESOURCES_DIRECTORY = "resources"


@bp.route("/files/<map_identifier>/<topic_identifier>")
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

    file_occurrences = store.get_topic_occurrences(
        map_identifier,
        topic_identifier,
        "file",
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    files = []
    for file_occurrence in file_occurrences:
        files.append(
            {
                "identifier": file_occurrence.identifier,
                "title": file_occurrence.get_attribute_by_name("title").value,
                "scope": file_occurrence.scope,
                "url": file_occurrence.resource_ref,
            }
        )

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "file/index.html",
        topic_map=topic_map,
        topic=topic,
        files=files,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/files/upload/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def upload(map_identifier, topic_identifier):
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
        form_file_title = request.form["file-title"].strip()
        form_file_scope = request.form["file-scope"].strip()
        form_upload_file = request.files["file-file"] if "file-file" in request.files else None

        # If no values have been provided set their default values
        if not form_file_scope:
            form_file_scope = session["current_scope"]

        # Validate form inputs
        if not form_file_title:
            error = error | 1
        if not form_upload_file:
            error = error | 2
        else:
            if form_upload_file.filename == "":
                error = error | 4
        if not store.topic_exists(topic_map.identifier, form_file_scope):
            error = error | 8

        if error != 0:
            flash(
                "An error occurred when uploading the file. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            file_extension = get_file_extension(form_upload_file.filename)
            file_file_name = f"{str(uuid.uuid4())}.{file_extension}"
            form_file_title = f"{form_file_title} (.{file_extension})"

            # Create the file directory for this topic map if it doesn't already exist
            file_directory = os.path.join(current_app.static_folder, RESOURCES_DIRECTORY, str(map_identifier))
            if not os.path.isdir(file_directory):
                os.makedirs(file_directory)

            file_path = os.path.join(file_directory, file_file_name)
            form_upload_file.save(file_path)

            file_occurrence = Occurrence(
                instance_of="file",
                topic_identifier=topic.identifier,
                scope=form_file_scope,
                resource_ref=file_file_name,
            )
            title_attribute = Attribute(
                "title",
                form_file_title,
                file_occurrence.identifier,
                data_type=DataType.STRING,
            )

            # Persist objects to the topic store
            store.create_occurrence(topic_map.identifier, file_occurrence)
            store.create_attribute(topic_map.identifier, title_attribute)

            flash("File successfully uploaded.", "success")
            return redirect(
                url_for(
                    "file.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

        return render_template(
            "file/upload.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            file_title=form_file_title,
            file_scope=form_file_scope,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "file/upload.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/files/edit/<map_identifier>/<topic_identifier>/<file_identifier>",
    methods=("GET", "POST"),
)
@login_required
def edit(map_identifier, topic_identifier, file_identifier):
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

    file_occurrence = store.get_occurrence(
        map_identifier,
        file_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    form_file_title = file_occurrence.get_attribute_by_name("title").value
    form_file_scope = file_occurrence.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_file_title = request.form["file-title"].strip()
        form_file_scope = request.form["file-scope"].strip()

        # If no values have been provided set their default values
        if not form_file_scope:
            form_file_scope = session["current_scope"]

        # Validate form inputs
        if not form_file_title:
            error = error | 1
        if not store.topic_exists(topic_map.identifier, form_file_scope):
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            # Update file's title if it has changed
            if file_occurrence.get_attribute_by_name("title").value != form_file_title:
                store.update_attribute_value(
                    topic_map.identifier,
                    file_occurrence.get_attribute_by_name("title").identifier,
                    form_file_title,
                )

            # Update file's scope if it has changed
            if file_occurrence.scope != form_file_scope:
                store.update_occurrence_scope(map_identifier, file_occurrence.identifier, form_file_scope)

            flash("File successfully updated.", "success")
            return redirect(
                url_for(
                    "file.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    return render_template(
        "file/edit.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        file_identifier=file_occurrence.identifier,
        file_title=form_file_title,
        file_scope=form_file_scope,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/files/delete/<map_identifier>/<topic_identifier>/<file_identifier>",
    methods=("GET", "POST"),
)
@login_required
def delete(map_identifier, topic_identifier, file_identifier):
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

    file_occurrence = store.get_occurrence(
        map_identifier,
        file_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    form_file_title = file_occurrence.get_attribute_by_name("title").value
    form_file_scope = file_occurrence.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    if request.method == "POST":
        # Delete file occurrence from topic store
        store.delete_occurrence(map_identifier, file_occurrence.identifier)

        # Delete file from file system
        file_file_path = os.path.join(
            current_app.static_folder,
            RESOURCES_DIRECTORY,
            str(map_identifier),
            file_occurrence.resource_ref,
        )
        if os.path.exists(file_file_path):
            os.remove(file_file_path)

        flash("File successfully deleted.", "warning")
        return redirect(
            url_for(
                "file.index",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
            )
        )

    return render_template(
        "file/delete.html",
        topic_map=topic_map,
        topic=topic,
        file_identifier=file_occurrence.identifier,
        file_title=form_file_title,
        file_scope=form_file_scope,
        map_notes_count=map_notes_count,
    )


# ========== HELPER METHODS ==========


def get_file_extension(file_name):
    return file_name.rsplit(".", 1)[1].lower()
