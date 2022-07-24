"""
topic.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import os
import shutil
from collections import deque
from datetime import datetime

import maya
import mistune
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_security import current_user, login_required
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.basename import BaseName
from topicdb.core.models.collaborationmode import CollaborationMode
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.models.topic import Topic
from topicdb.core.store.retrievalmode import RetrievalMode
from topicdb.core.topicdberror import TopicDbError
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store
from contextualise.utilities.highlight_renderer import HighlightRenderer

bp = Blueprint("topic", __name__)

RESOURCES_DIRECTORY = "static/resources/"
BREADCRUMBS_COUNT = 4
UNIVERSAL_SCOPE = "*"
RESPONSE = 0
STATUS_CODE = 1


@bp.route("/topics/view/<map_identifier>/<topic_identifier>")
def view(map_identifier, topic_identifier):
    store = get_topic_store()

    collaboration_mode = None
    is_map_owner = False
    if current_user.is_authenticated:  # User is logged in
        is_map_owner = store.is_map_owner(map_identifier, current_user.id)
        if is_map_owner:
            topic_map = store.get_map(map_identifier, current_user.id)
        else:
            topic_map = store.get_map(map_identifier)
        if topic_map is None:
            current_app.logger.warning(
                f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
            )
            abort(404)
        collaboration_mode = store.get_collaboration_mode(map_identifier, current_user.id)
        if topic_map.published:
            if not is_map_owner and topic_identifier == "home":
                flash(
                    "You are accessing a published topic map of another user.",
                    "primary",
                )
        else:
            if not is_map_owner:  # The map is private and doesn't belong to the user who is trying to access it
                if not collaboration_mode:  # The user is not collaborating on the map
                    abort(403)
    else:  # User is not logged in
        topic_map = store.get_map(map_identifier)
        if topic_map is None:
            current_app.logger.warning(
                f"Topic map not found: user identifier: [N/A], topic map identifier: [{map_identifier}]"
            )
            abort(404)
        if not topic_map.published:  # User is not logged in and the map is not published
            abort(403)

    # Determine if (active) scope filtering has been specified in the URL
    scope_filtered = request.args.get("filter", type=int)
    if scope_filtered is not None:
        session["scope_filter"] = scope_filtered
    if "scope_filter" in session:
        scope_filtered = session["scope_filter"]
    else:
        session["breadcrumbs"] = []
        session["current_scope"] = UNIVERSAL_SCOPE
        session["scope_filter"] = 1

    # If a scope has been specified in the URL, then use that to set the scope
    scope_identifier = request.args.get("scope", type=str)
    if scope_identifier and store.topic_exists(map_identifier, scope_identifier):
        session["current_scope"] = scope_identifier

    # Get topic
    if scope_filtered:
        topic = store.get_topic(
            map_identifier,
            topic_identifier,
            scope=session["current_scope"],
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )
    else:
        topic = store.get_topic(
            map_identifier,
            topic_identifier,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )
    if topic is None:
        if current_user.is_authenticated:  # User is logged in
            current_app.logger.warning(
                f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
            )
        else:
            current_app.logger.warning(
                f"Topic not found: user identifier: [N/A], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
            )
        session["inexistent_topic_identifier"] = topic_identifier
        abort(404)
    else:
        session.pop("inexistent_topic_identifier", None)

    if scope_filtered:
        topic_occurrences = store.get_topic_occurrences(
            map_identifier,
            topic_identifier,
            scope=session["current_scope"],
            inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )
    else:
        topic_occurrences = store.get_topic_occurrences(
            map_identifier,
            topic_identifier,
            inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )
    occurrences = {
        "text": None,
        "images": [],
        "3d-scenes": [],
        "files": [],
        "links": [],
        "videos": [],
        "notes": [],
    }
    for occurrence in topic_occurrences:
        if occurrence.instance_of == "text" and occurrence.scope == session["current_scope"]:
            if occurrence.resource_data:
                markdown = mistune.create_markdown(
                    renderer=HighlightRenderer(escape=False),
                    plugins=[
                        "strikethrough",
                        "footnotes",
                        "table",
                    ],
                )
                occurrences["text"] = markdown(occurrence.resource_data.decode())
        elif occurrence.instance_of == "image":
            occurrences["images"].append(
                {
                    "title": occurrence.get_attribute_by_name("title").value,
                    "url": occurrence.resource_ref,
                }
            )
        elif occurrence.instance_of == "3d-scene":
            occurrences["3d-scenes"].append(
                {
                    "title": occurrence.get_attribute_by_name("title").value,
                    "url": occurrence.resource_ref,
                }
            )
        elif occurrence.instance_of == "file":
            occurrences["files"].append(
                {
                    "title": occurrence.get_attribute_by_name("title").value,
                    "url": occurrence.resource_ref,
                }
            )
        elif occurrence.instance_of == "url":
            occurrences["links"].append(
                {
                    "title": occurrence.get_attribute_by_name("title").value,
                    "url": occurrence.resource_ref,
                }
            )
        elif occurrence.instance_of == "video":
            occurrences["videos"].append(
                {
                    "title": occurrence.get_attribute_by_name("title").value,
                    "url": occurrence.resource_ref,
                }
            )
        elif occurrence.instance_of == "note":
            markdown = mistune.create_markdown(
                renderer=HighlightRenderer(escape=False),
                plugins=[
                    "strikethrough",
                    "footnotes",
                    "table",
                ],
            )
            occurrences["notes"].append(
                {
                    "identifier": occurrence.identifier,
                    "title": occurrence.get_attribute_by_name("title").value,
                    "timestamp": maya.parse(occurrence.get_attribute_by_name("modification-timestamp").value),
                    "text": markdown(occurrence.resource_data.decode()),
                }
            )
    if scope_filtered:
        associations = store.get_association_groups(map_identifier, topic_identifier, scope=session["current_scope"])
    else:
        associations = store.get_association_groups(map_identifier, topic_identifier)

    is_knowledge_path_topic = (
        ("navigation", "up") in associations
        or ("navigation", "down") in associations
        or ("navigation", "previous") in associations
        or ("navigation", "next") in associations
    )

    creation_date = maya.parse(topic.get_attribute_by_name("creation-timestamp").value)
    modification_date_attribute = topic.get_attribute_by_name("modification-timestamp")
    modification_date = maya.parse(modification_date_attribute.value) if modification_date_attribute else "Undefined"

    # Breadcrumbs
    if "map_identifier" not in session:
        session["map_identifier"] = topic_map.identifier
    elif session["map_identifier"] != topic_map.identifier:
        session["breadcrumbs"] = []
    session["map_identifier"] = topic_map.identifier

    if "breadcrumbs" not in session:
        session["breadcrumbs"] = []
    breadcrumbs = deque(session["breadcrumbs"], BREADCRUMBS_COUNT)
    if topic_identifier in breadcrumbs:
        breadcrumbs.remove(topic_identifier)
    breadcrumbs.append(topic_identifier)
    session["breadcrumbs"] = list(breadcrumbs)

    from contextualise import api

    associations_state = api.get_association_groups(
        map_identifier, topic_identifier, session["current_scope"], scope_filtered
    )
    associations_state = (
        associations_state[RESPONSE].data.decode("utf-8") if associations_state[STATUS_CODE] == 200 else None
    )

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "topic/view.html",
        topic_map=topic_map,
        topic=topic,
        occurrences=occurrences,
        associations=associations,
        associations_state=associations_state,
        is_knowledge_path_topic=is_knowledge_path_topic,
        creation_date=creation_date,
        modification_date=modification_date,
        breadcrumbs=breadcrumbs,
        collaboration_mode=collaboration_mode,
        is_map_owner=is_map_owner,
        map_notes_count=map_notes_count,
    )


@bp.route("/topics/create/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def create(map_identifier, topic_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
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
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_topic_identifier = request.form["topic-identifier"].strip()
        form_topic_name = request.form["topic-name"].strip()
        form_topic_text = request.form["topic-text"].strip()
        form_topic_instance_of = request.form["topic-instance-of"].strip()
        form_topic_text_scope = request.form["topic-text-scope"].strip()

        # If no values have been provided set their default values
        if not form_topic_instance_of:
            form_topic_instance_of = "topic"
        if not form_topic_text_scope:
            form_topic_text_scope = session["current_scope"]

        # Validate form inputs
        if not form_topic_name:
            error = error | 1
        if store.topic_exists(topic_map.identifier, form_topic_identifier):
            error = error | 2
        if not form_topic_identifier:
            error = error | 4
        if not store.topic_exists(topic_map.identifier, form_topic_instance_of):
            error = error | 8
        if not store.topic_exists(topic_map.identifier, form_topic_text_scope):
            error = error | 16

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            new_topic = Topic(form_topic_identifier, form_topic_instance_of, form_topic_name)
            text_occurrence = Occurrence(
                instance_of="text",
                topic_identifier=new_topic.identifier,
                scope=form_topic_text_scope,
                resource_data=form_topic_text,
            )

            new_topic.first_base_name.scope = session["current_scope"]

            timestamp = str(datetime.now())
            modification_attribute = Attribute(
                "modification-timestamp",
                timestamp,
                new_topic.identifier,
                data_type=DataType.TIMESTAMP,
            )

            # Persist objects to the topic store
            store.create_topic(topic_map.identifier, new_topic)
            store.create_occurrence(topic_map.identifier, text_occurrence)
            store.create_attribute(topic_map.identifier, modification_attribute)

            flash("Topic successfully created.", "success")
            return redirect(
                url_for(
                    "topic.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=new_topic.identifier,
                )
            )

        return render_template(
            "topic/create.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            topic_name=form_topic_name,
            topic_identifier=form_topic_identifier,
            topic_text=form_topic_text,
            topic_instance_of=form_topic_instance_of,
            topic_text_scope=form_topic_text_scope,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "topic/create.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route("/topics/edit/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def edit(map_identifier, topic_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        scope=session["current_scope"],
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    occurrences = store.get_topic_occurrences(
        map_identifier,
        topic_identifier,
        scope=session["current_scope"],
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
    )

    texts = [
        occurrence
        for occurrence in occurrences
        if occurrence.instance_of == "text" and occurrence.scope == session["current_scope"]
    ]

    form_topic_name = topic.first_base_name.name
    form_topic_text = texts[0].resource_data.decode() if len(texts) > 0 and texts[0].resource_data else ""
    form_topic_instance_of = topic.instance_of
    form_topic_text_scope = texts[0].scope if len(texts) > 0 else session["current_scope"]

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_topic_name = request.form["topic-name"].strip()
        form_topic_text = request.form["topic-text"].strip()
        form_topic_instance_of = request.form["topic-instance-of"].strip()
        form_topic_text_scope = request.form["topic-text-scope"].strip()

        # If no values have been provided set their default values
        if not form_topic_instance_of:
            form_topic_instance_of = "topic"
        if not form_topic_text_scope:
            form_topic_text_scope = session["current_scope"]

        # Validate form inputs
        if not store.topic_exists(topic_map.identifier, form_topic_instance_of):
            error = error | 1
        if not store.topic_exists(topic_map.identifier, form_topic_text_scope):
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            if topic.get_base_name_by_scope(session["current_scope"]):
                # Update the topic's base name if it has changed
                if topic.first_base_name.name != form_topic_name:
                    store.update_base_name(
                        map_identifier,
                        topic.first_base_name.identifier,
                        form_topic_name,
                        form_topic_text_scope,
                    )
            else:
                base_name = BaseName(form_topic_name, session["current_scope"])
                store.create_base_name(map_identifier, topic.identifier, base_name)

            # Update topic's 'instance of' if it has changed
            if topic.instance_of != form_topic_instance_of:
                store.update_topic_instance_of(map_identifier, topic.identifier, form_topic_instance_of)

            # If the topic has an existing text occurrence update it, otherwise create a new text occurrence
            # and persist it
            if len(texts) > 0 and form_topic_text_scope == session["current_scope"]:
                store.update_occurrence_data(map_identifier, texts[0].identifier, form_topic_text)
            else:
                text_occurrence = Occurrence(
                    instance_of="text",
                    topic_identifier=topic.identifier,
                    scope=form_topic_text_scope,
                    resource_data=form_topic_text,
                )
                store.create_occurrence(topic_map.identifier, text_occurrence)

            # Update the topic's modification (timestamp) attribute
            timestamp = str(datetime.now())
            if topic.get_attribute_by_name("modification-timestamp"):
                store.update_attribute_value(
                    topic_map.identifier,
                    topic.get_attribute_by_name("modification-timestamp").identifier,
                    timestamp,
                )
            else:
                modification_attribute = Attribute(
                    "modification-timestamp",
                    timestamp,
                    topic.identifier,
                    data_type=DataType.TIMESTAMP,
                )
                store.create_attribute(topic_map.identifier, modification_attribute)

            flash("Topic successfully updated.", "success")
            return redirect(
                url_for(
                    "topic.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    return render_template(
        "topic/edit.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        topic_name=form_topic_name,
        topic_identifier=topic.identifier,
        topic_text=form_topic_text,
        topic_instance_of=form_topic_instance_of,
        topic_text_scope=form_topic_text_scope,
        collaboration_mode=topic_map.collaboration_mode,
        map_notes_count=map_notes_count,
    )


@bp.route("/topics/delete/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def delete(map_identifier, topic_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
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
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    if request.method == "POST":
        try:
            # Remove the topic from the topic store
            store.delete_topic(map_identifier, topic_identifier)

            # Clear the breadcrumbs (of which this topic was part of)
            session["breadcrumbs"] = []

            # Remove the topic's resources directory
            topic_directory = os.path.join(bp.root_path, RESOURCES_DIRECTORY, str(map_identifier), topic_identifier)
            if os.path.isdir(topic_directory):
                shutil.rmtree(topic_directory)
        except TopicDbError:
            flash(
                "Topic not deleted. Certain predefined topics cannot be deleted. Alternatively, you attempted to delete an association.",
                "warning",
            )
            return redirect(
                url_for(
                    "topic.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic_identifier,
                )
            )

        flash("Topic successfully deleted.", "success")
        return redirect(
            url_for(
                "topic.view",
                map_identifier=topic_map.identifier,
                topic_identifier="home",
            )
        )

    return render_template(
        "topic/delete.html",
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route("/topics/add-note/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add_note(map_identifier, topic_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and (
        topic_map.collaboration_mode is not CollaborationMode.EDIT
        and topic_map.collaboration_mode is not CollaborationMode.COMMENT
    ):
        abort(403)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_note_title = request.form["note-title"].strip()
        form_note_text = request.form["note-text"].strip()
        form_note_scope = request.form["note-scope"].strip()

        # If no values have been provided set their default values
        if not form_note_scope:
            form_note_scope = session["current_scope"]

        # Validate form inputs
        if not form_note_title:
            error = error | 1
        if not form_note_text:
            error = error | 2
        if not store.topic_exists(topic_map.identifier, form_note_scope):
            error = error | 4

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            note_occurrence = Occurrence(
                instance_of="note",
                topic_identifier=topic.identifier,
                scope=form_note_scope,
                resource_data=form_note_text,
            )
            title_attribute = Attribute(
                "title",
                form_note_title,
                note_occurrence.identifier,
                data_type=DataType.STRING,
            )
            timestamp = str(datetime.now())
            modification_attribute = Attribute(
                "modification-timestamp",
                timestamp,
                note_occurrence.identifier,
                data_type=DataType.TIMESTAMP,
            )

            # Persist objects to the topic store
            store.create_occurrence(topic_map.identifier, note_occurrence)
            store.create_attribute(topic_map.identifier, title_attribute)
            store.create_attribute(topic_map.identifier, modification_attribute)

            flash("Note successfully added.", "success")
            return redirect(
                url_for(
                    "topic.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

        return render_template(
            "topic/add_note.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            note_title=form_note_title,
            note_text=form_note_text,
            note_scope=form_note_scope,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "topic/add_note.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/topics/edit-note/<map_identifier>/<topic_identifier>/<note_identifier>",
    methods=("GET", "POST"),
)
@login_required
def edit_note(map_identifier, topic_identifier, note_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and (
        topic_map.collaboration_mode is not CollaborationMode.EDIT
        and topic_map.collaboration_mode is not CollaborationMode.COMMENT
    ):
        abort(403)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if topic is None:
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    note_occurrence = store.get_occurrence(
        map_identifier,
        note_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    form_note_title = note_occurrence.get_attribute_by_name("title").value
    form_note_text = note_occurrence.resource_data.decode()
    form_note_scope = note_occurrence.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_note_title = request.form["note-title"].strip()
        form_note_text = request.form["note-text"].strip()
        form_note_scope = request.form["note-scope"].strip()

        # If no values have been provided set their default values
        if not form_note_scope:
            form_note_scope = session["current_scope"]

        # Validate form inputs
        if not form_note_title:
            error = error | 1
        if not form_note_text:
            error = error | 2
        if not store.topic_exists(topic_map.identifier, form_note_scope):
            error = error | 4

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            # Update note's title if it has changed
            if note_occurrence.get_attribute_by_name("title").value != form_note_title:
                store.update_attribute_value(
                    topic_map.identifier,
                    note_occurrence.get_attribute_by_name("title").identifier,
                    form_note_title,
                )

            # Update the note's modification (timestamp) attribute
            timestamp = str(datetime.now())
            store.update_attribute_value(
                topic_map.identifier,
                note_occurrence.get_attribute_by_name("modification-timestamp").identifier,
                timestamp,
            )

            # Update note (occurrence)
            store.update_occurrence_data(map_identifier, note_occurrence.identifier, form_note_text)

            # Update note's scope if it has changed
            if note_occurrence.scope != form_note_scope:
                store.update_occurrence_scope(map_identifier, note_occurrence.identifier, form_note_scope)

            flash("Note successfully updated.", "success")
            return redirect(
                url_for(
                    "topic.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    return render_template(
        "topic/edit_note.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        note_identifier=note_occurrence.identifier,
        note_title=form_note_title,
        note_text=form_note_text,
        note_scope=form_note_scope,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/topics/delete-note/<map_identifier>/<topic_identifier>/<note_identifier>",
    methods=("GET", "POST"),
)
@login_required
def delete_note(map_identifier, topic_identifier, note_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and (
        topic_map.collaboration_mode is not CollaborationMode.EDIT
        and topic_map.collaboration_mode is not CollaborationMode.COMMENT
    ):
        abort(403)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if topic is None:
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    note_occurrence = store.get_occurrence(
        map_identifier,
        note_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    form_note_title = note_occurrence.get_attribute_by_name("title").value
    markdown = mistune.create_markdown(
        renderer=HighlightRenderer(escape=False),
        plugins=[
            "strikethrough",
            "footnotes",
            "table",
        ],
    )
    form_note_text = markdown(note_occurrence.resource_data.decode())
    form_note_scope = note_occurrence.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    if request.method == "POST":
        store.delete_occurrence(map_identifier, note_occurrence.identifier)
        flash("Note successfully deleted.", "warning")
        return redirect(
            url_for(
                "topic.view",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
            )
        )

    return render_template(
        "topic/delete_note.html",
        topic_map=topic_map,
        topic=topic,
        note_identifier=note_occurrence.identifier,
        note_title=form_note_title,
        note_text=form_note_text,
        note_scope=form_note_scope,
        map_notes_count=map_notes_count,
    )


@bp.route("/topics/view-names/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def view_names(map_identifier, topic_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
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
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "topic/view_names.html",
        topic_map=topic_map,
        topic=topic,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/topics/add-name/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add_name(map_identifier, topic_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
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
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_topic_name = request.form["topic-name"].strip()
        form_topic_name_scope = request.form["topic-name-scope"].strip()

        # If no values have been provided set their default values
        if not form_topic_name_scope:
            form_topic_name_scope = session["current_scope"]

        # Validate form inputs
        if not form_topic_name:
            error = error | 1
        if not store.topic_exists(topic_map.identifier, form_topic_name_scope):
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            base_name = BaseName(form_topic_name, scope=form_topic_name_scope)
            store.create_base_name(map_identifier, topic.identifier, base_name)

            flash("Name successfully added.", "success")
            return redirect(
                url_for(
                    "topic.view_names",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

        return render_template(
            "topic/add_name.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            topic_name=form_topic_name,
            topic_name_scope=form_topic_name_scope,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "topic/add_name.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/topics/edit-name/<map_identifier>/<topic_identifier>/<name_identifier>",
    methods=("GET", "POST"),
)
@login_required
def edit_name(map_identifier, topic_identifier, name_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
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
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    form_topic_name = topic.get_base_name(name_identifier).name
    form_topic_name_scope = topic.get_base_name(name_identifier).scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_topic_name = request.form["topic-name"].strip()
        form_topic_name_scope = request.form["topic-name-scope"].strip()

        # If no values have been provided set their default values
        if not form_topic_name_scope:
            form_topic_name_scope = session["current_scope"]

        # Validate form inputs
        if not form_topic_name:
            error = error | 1
        if not store.topic_exists(topic_map.identifier, form_topic_name_scope):
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            # Update name if required
            if (
                form_topic_name != topic.get_base_name(name_identifier).name
                or form_topic_name_scope != topic.get_base_name(name_identifier).scope
            ):
                store.update_base_name(
                    map_identifier,
                    name_identifier,
                    form_topic_name,
                    scope=form_topic_name_scope,
                )

            flash("Name successfully updated.", "success")
            return redirect(
                url_for(
                    "topic.view_names",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    return render_template(
        "topic/edit_name.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        topic_name=form_topic_name,
        topic_name_scope=form_topic_name_scope,
        name_identifier=name_identifier,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/topics/delete-name/<map_identifier>/<topic_identifier>/<name_identifier>",
    methods=("GET", "POST"),
)
@login_required
def delete_name(map_identifier, topic_identifier, name_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
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
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    form_topic_name = topic.get_base_name(name_identifier).name
    form_topic_name_scope = topic.get_base_name(name_identifier).scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    if request.method == "POST":
        store.delete_base_name(map_identifier, name_identifier)

        flash("Name successfully deleted.", "warning")
        return redirect(
            url_for(
                "topic.view_names",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
            )
        )

    return render_template(
        "topic/delete_name.html",
        topic_map=topic_map,
        topic=topic,
        topic_name=form_topic_name,
        topic_name_scope=form_topic_name_scope,
        name_identifier=name_identifier,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/topics/change-scope/<map_identifier>/<topic_identifier>/<scope_identifier>",
    methods=("GET", "POST"),
)
@login_required
def change_scope(map_identifier, topic_identifier, scope_identifier):
    store = get_topic_store()
    topic_map = store.get_map(map_identifier, current_user.id)

    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
        abort(404)

    topic = store.get_topic(
        map_identifier,
        topic_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if topic is None:
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    form_scope = scope_identifier
    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_scope = request.form["new-scope"].strip()

        # If no values have been provided set their default values
        if not form_scope:
            form_scope = UNIVERSAL_SCOPE

        # Validate form inputs
        if not store.topic_exists(topic_map.identifier, form_scope):
            error = error | 1

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            session["current_scope"] = form_scope
            flash("Scope successfully changed.", "success")
            return redirect(
                url_for(
                    "topic.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    return render_template(
        "topic/change_scope.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        scope_identifier=form_scope,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/topics/edit-identifier/<map_identifier>/<topic_identifier>",
    methods=("GET", "POST"),
)
@login_required
def edit_identifier(map_identifier, topic_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        current_app.logger.warning(
            f"Topic map not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}]"
        )
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
        current_app.logger.warning(
            f"Topic not found: user identifier: [{current_user.id}], topic map identifier: [{map_identifier}], topic identifier: [{topic_identifier}]"
        )
        abort(404)

    form_topic_identifier = topic.identifier
    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_topic_identifier = request.form["topic-identifier"].strip()

        # Validate form inputs
        if not form_topic_identifier:
            error = error | 1
        if store.topic_exists(topic_map.identifier, form_topic_identifier):
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            # Update topic identifier
            try:
                store.update_topic_identifier(map_identifier, topic_identifier, form_topic_identifier)
            except TopicDbError:
                flash(
                    "Topic identifier not updated. Certain predefined topics cannot be modified.",
                    "warning",
                )
                return redirect(
                    url_for(
                        "topic.edit_identifier",
                        map_identifier=topic_map.identifier,
                        topic_identifier=topic_identifier,
                    )
                )

            flash("Identifier successfully updated.", "success")
            return redirect(
                url_for(
                    "topic.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=form_topic_identifier,
                )
            )

    return render_template(
        "topic/edit_identifier.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        topic_identifier=form_topic_identifier,
        map_notes_count=map_notes_count,
    )
