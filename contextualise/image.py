"""
image.py file. Part of the Contextualise project.

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

bp = Blueprint("image", __name__)

RESOURCES_DIRECTORY = "resources"
EXTENSIONS_WHITELIST = {"png", "jpg", "jpeg", "gif"}


@bp.route("/images/<map_identifier>/<topic_identifier>")
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

    image_occurrences = store.get_topic_occurrences(
        map_identifier,
        topic_identifier,
        "image",
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    images = []
    for image_occurrence in image_occurrences:
        images.append(
            {
                "identifier": image_occurrence.identifier,
                "title": image_occurrence.get_attribute_by_name("title").value,
                "scope": image_occurrence.scope,
                "url": image_occurrence.resource_ref,
            }
        )

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "image/index.html",
        topic_map=topic_map,
        topic=topic,
        images=images,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/images/upload/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
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
        form_image_title = request.form["image-title"].strip()
        form_image_scope = request.form["image-scope"].strip()
        form_upload_file = request.files["image-file"] if "image-file" in request.files else None

        # If no values have been provided set their default values
        if not form_image_scope:
            form_image_scope = session["current_scope"]

        # Validate form inputs
        if not form_image_title:
            error = error | 1
        if not form_upload_file:
            error = error | 2
        else:
            if form_upload_file.filename == "":
                error = error | 4
            elif not allowed_file(form_upload_file.filename):
                error = error | 8
        if not store.topic_exists(topic_map.identifier, form_image_scope):
            error = error | 16

        if error != 0:
            flash(
                "An error occurred when uploading the image. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            image_file_name = f"{str(uuid.uuid4())}.{get_file_extension(form_upload_file.filename)}"

            # Create the image directory for this topic map if it doesn't already exist
            image_directory = os.path.join(current_app.static_folder, RESOURCES_DIRECTORY, str(map_identifier))
            if not os.path.isdir(image_directory):
                os.makedirs(image_directory)

            file_path = os.path.join(image_directory, image_file_name)
            form_upload_file.save(file_path)

            image_occurrence = Occurrence(
                instance_of="image",
                topic_identifier=topic.identifier,
                scope=form_image_scope,
                resource_ref=image_file_name,
            )
            title_attribute = Attribute(
                "title",
                form_image_title,
                image_occurrence.identifier,
                data_type=DataType.STRING,
            )

            # Persist objects to the topic store
            store.create_occurrence(topic_map.identifier, image_occurrence)
            store.create_attribute(topic_map.identifier, title_attribute)

            flash("Image successfully uploaded.", "success")
            return redirect(
                url_for(
                    "image.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

        return render_template(
            "image/upload.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            image_title=form_image_title,
            image_scope=form_image_scope,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "image/upload.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/images/edit/<map_identifier>/<topic_identifier>/<image_identifier>",
    methods=("GET", "POST"),
)
@login_required
def edit(map_identifier, topic_identifier, image_identifier):
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

    image_occurrence = store.get_occurrence(
        map_identifier,
        image_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    form_image_title = image_occurrence.get_attribute_by_name("title").value
    form_image_resource_ref = image_occurrence.resource_ref
    form_image_scope = image_occurrence.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_image_title = request.form["image-title"].strip()
        form_image_scope = request.form["image-scope"].strip()

        # If no values have been provided set their default values
        if not form_image_scope:
            form_image_scope = session["current_scope"]

        # Validate form inputs
        if not form_image_title:
            error = error | 1
        if not store.topic_exists(topic_map.identifier, form_image_scope):
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            # Update image's title if it has changed
            if image_occurrence.get_attribute_by_name("title").value != form_image_title:
                store.update_attribute_value(
                    topic_map.identifier,
                    image_occurrence.get_attribute_by_name("title").identifier,
                    form_image_title,
                )

            # Update image's scope if it has changed
            if image_occurrence.scope != form_image_scope:
                store.update_occurrence_scope(map_identifier, image_occurrence.identifier, form_image_scope)

            flash("Image successfully updated.", "success")
            return redirect(
                url_for(
                    "image.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    return render_template(
        "image/edit.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        image_identifier=image_occurrence.identifier,
        image_title=form_image_title,
        image_resource_ref=form_image_resource_ref,
        image_scope=form_image_scope,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/images/delete/<map_identifier>/<topic_identifier>/<image_identifier>",
    methods=("GET", "POST"),
)
@login_required
def delete(map_identifier, topic_identifier, image_identifier):
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

    image_occurrence = store.get_occurrence(
        map_identifier,
        image_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    form_image_title = image_occurrence.get_attribute_by_name("title").value
    form_image_resource_ref = image_occurrence.resource_ref
    form_image_scope = image_occurrence.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    if request.method == "POST":
        # Delete image occurrence from topic store
        store.delete_occurrence(map_identifier, image_occurrence.identifier)

        # Delete image from file system
        image_file_path = os.path.join(
            current_app.static_folder,
            RESOURCES_DIRECTORY,
            str(map_identifier),
            image_occurrence.resource_ref,
        )
        if os.path.exists(image_file_path):
            os.remove(image_file_path)

        flash("Image successfully deleted.", "warning")
        return redirect(
            url_for(
                "image.index",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
            )
        )

    return render_template(
        "image/delete.html",
        topic_map=topic_map,
        topic=topic,
        image_identifier=image_occurrence.identifier,
        image_title=form_image_title,
        image_resource_ref=form_image_resource_ref,
        image_scope=form_image_scope,
        map_notes_count=map_notes_count,
    )


# ========== HELPER METHODS ==========


def get_file_extension(file_name):
    return file_name.rsplit(".", 1)[1].lower()


def allowed_file(file_name):
    return get_file_extension(file_name) in EXTENSIONS_WHITELIST
