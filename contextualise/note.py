"""
note.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from datetime import datetime

import maya
import mistune
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_security import current_user, login_required
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.collaborationmode import CollaborationMode
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.models.topic import Topic
from topicdb.core.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store
from contextualise.utilities.highlight_renderer import HighlightRenderer

bp = Blueprint("note", __name__)


@bp.route("/notes/index/<map_identifier>")
def index(map_identifier):
    store = get_topic_store()

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

    topic = store.get_topic(map_identifier, "notes")
    if topic is None:
        abort(404)

    note_occurrences = store.get_topic_occurrences(
        map_identifier,
        "notes",
        "note",
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    notes = []
    markdown = mistune.create_markdown(
        renderer=HighlightRenderer(escape=False),
        plugins=[
            "strikethrough",
            "footnotes",
            "table",
        ],
    )
    for note_occurrence in note_occurrences:
        notes.append(
            {
                "identifier": note_occurrence.identifier,
                "title": note_occurrence.get_attribute_by_name("title").value,
                "timestamp": maya.parse(note_occurrence.get_attribute_by_name("modification-timestamp").value),
                "text": markdown(note_occurrence.resource_data.decode()),
            }
        )

    return render_template("note/index.html", topic_map=topic_map, topic=topic, notes=notes)


@bp.route("/notes/add/<map_identifier>", methods=("GET", "POST"))
@login_required
def add(map_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = store.get_topic(map_identifier, "notes", resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

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
                topic_identifier="notes",
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
            return redirect(url_for("note.index", map_identifier=topic_map.identifier))

        return render_template(
            "note/add.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            note_title=form_note_title,
            note_text=form_note_text,
            note_scope=form_note_scope,
        )

    return render_template("note/add.html", error=error, topic_map=topic_map, topic=topic)


@bp.route("/notes/attach/<map_identifier>/<note_identifier>", methods=("GET", "POST"))
@login_required
def attach(map_identifier, note_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = store.get_topic(map_identifier, "notes", resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES)
    if topic is None:
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

    error = 0

    if request.method == "POST":
        form_note_topic_identifier = request.form["note-topic-identifier"].strip()

        # Validate form inputs
        if not store.topic_exists(topic_map.identifier, form_note_topic_identifier):
            error = error | 1

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            store.update_occurrence_topic_identifier(map_identifier, note_identifier, form_note_topic_identifier)
            flash("Note successfully attached.", "success")
            return redirect(
                url_for(
                    "topic.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=form_note_topic_identifier,
                )
            )

    return render_template(
        "note/attach.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        note_identifier=note_occurrence.identifier,
        note_title=form_note_title,
        note_text=form_note_text,
        note_scope=form_note_scope,
    )


@bp.route("/notes/convert/<map_identifier>/<note_identifier>", methods=("GET", "POST"))
@login_required
def convert(map_identifier, note_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = store.get_topic(map_identifier, "notes", resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    note_occurrence = store.get_occurrence(
        map_identifier,
        note_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    note_title = note_occurrence.get_attribute_by_name("title").value

    form_topic_name = ""
    form_topic_identifier = ""
    form_topic_text = "## " + note_title + "\n" + note_occurrence.resource_data.decode()

    error = 0

    if request.method == "POST":
        form_topic_identifier = request.form["topic-identifier"].strip()
        form_topic_name = request.form["topic-name"].strip()
        form_topic_text = request.form["topic-text"]
        form_topic_instance_of = request.form["topic-instance-of"].strip()

        # If no values have been provided set their default values
        if not form_topic_instance_of:
            form_topic_instance_of = "topic"

        # Validate form inputs
        if not form_topic_name:
            error = error | 1
        if store.topic_exists(topic_map.identifier, form_topic_identifier):
            error = error | 2
        if not form_topic_identifier:
            error = error | 4
        if not store.topic_exists(topic_map.identifier, form_topic_instance_of):
            error = error | 8

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
                resource_data=form_topic_text,
            )
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

            # Remove the original note occurrence
            store.delete_occurrence(topic_map.identifier, note_identifier)

            flash("Note successfully converted.", "success")
            return redirect(
                url_for(
                    "topic.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=new_topic.identifier,
                )
            )

        return render_template(
            "note/convert.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            topic_name=form_topic_name,
            topic_identifier=form_topic_identifier,
            topic_text=form_topic_text,
            topic_instance_of=form_topic_instance_of,
            note_identifier=note_identifier,
        )

    return render_template(
        "note/convert.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        topic_name=form_topic_name,
        topic_identifier=form_topic_identifier,
        topic_text=form_topic_text,
        note_identifier=note_identifier,
    )


@bp.route("/notes/edit/<map_identifier>/<note_identifier>", methods=("GET", "POST"))
@login_required
def edit(map_identifier, note_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)

    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and (
        topic_map.collaboration_mode is not CollaborationMode.EDIT
        and topic_map.collaboration_mode is not CollaborationMode.COMMENT
    ):
        abort(403)

    topic = store.get_topic(map_identifier, "notes", resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES)
    if topic is None:
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
                    "note.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    return render_template(
        "note/edit.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        note_identifier=note_occurrence.identifier,
        note_title=form_note_title,
        note_text=form_note_text,
        note_scope=form_note_scope,
    )


@bp.route("/notes/delete/<map_identifier>/<note_identifier>", methods=("GET", "POST"))
@login_required
def delete(map_identifier, note_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)

    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and (
        topic_map.collaboration_mode is not CollaborationMode.EDIT
        and topic_map.collaboration_mode is not CollaborationMode.COMMENT
    ):
        abort(403)

    topic = store.get_topic(map_identifier, "notes", resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES)
    if topic is None:
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

    if request.method == "POST":
        store.delete_occurrence(map_identifier, note_occurrence.identifier)
        flash("Note successfully deleted.", "warning")
        return redirect(
            url_for(
                "note.index",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
            )
        )

    return render_template(
        "note/delete.html",
        topic_map=topic_map,
        topic=topic,
        note_identifier=note_occurrence.identifier,
        note_title=form_note_title,
        note_text=form_note_text,
        note_scope=form_note_scope,
    )
