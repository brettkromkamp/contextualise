"""
topic.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from collections import deque
from datetime import datetime

import maya
import mistune
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_security import current_user, login_required
from topicdb.models.attribute import Attribute
from topicdb.models.basename import BaseName
from topicdb.models.datatype import DataType
from topicdb.models.occurrence import Occurrence
from topicdb.models.topic import Topic
from topicdb.store.ontologymode import OntologyMode
from topicdb.store.retrievalmode import RetrievalMode
from topicdb.topicdberror import TopicDbError
from werkzeug.exceptions import abort

from contextualise.utilities.topicstore import initialize

from . import constants
from .topic_store import get_topic_store
from .utilities.highlight_renderer import HighlightRenderer

bp = Blueprint("topic", __name__)


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

    # Scope filtering, initially, can be in one of three states:
    #   - Unspecified (None)
    #   - Not active (0)
    #   - Active (1)

    # Determine if (active) scope filtering has been specified in either the URL or, previously,
    # in the session. If scope filtering is undefined then set it to be active (1).
    scope_filtered = request.args.get("filter", type=int)
    if scope_filtered is None:
        scope_filtered = session.get("scope_filter", default=1)

    if "scope_filter" not in session:
        session["breadcrumbs"] = []
        session["current_scope"] = constants.UNIVERSAL_SCOPE

    session["scope_filter"] = scope_filtered

    if scope_filtered:
        scope_identifier = session.get("current_scope", default="*")
        if not store.topic_exists(map_identifier, scope_identifier):
            session["current_scope"] = constants.UNIVERSAL_SCOPE

        # Get topic
        topic = store.get_topic(
            map_identifier,
            topic_identifier,
            scope=session["current_scope"],
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )

        # Get topic occurrences
        topic_occurrences = store.get_topic_occurrences(
            map_identifier,
            topic_identifier,
            scope=session["current_scope"],
            inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )

        # Get topic associations
        associations = store.get_association_groups(map_identifier, topic_identifier, scope=session["current_scope"])
    else:
        # Get topic
        topic = store.get_topic(
            map_identifier,
            topic_identifier,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )

        # Get topic occurrences
        topic_occurrences = store.get_topic_occurrences(
            map_identifier,
            topic_identifier,
            inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )

        # Get topic associations
        associations = store.get_association_groups(map_identifier, topic_identifier)

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

    occurrences = {
        "text": None,
        "images": [],
        "3d-scenes": [],
        "files": [],
        "links": [],
        "videos": [],
        "notes": [],
        "temporal-events": [],
        "temporal-eras": [],
    }
    for occurrence in topic_occurrences:
        match occurrence.instance_of:
            case "text":
                if occurrence.scope == session["current_scope"] and occurrence.resource_data:
                    markdown = mistune.create_markdown(
                        renderer=HighlightRenderer(escape=False),
                        plugins=[
                            "strikethrough",
                            "footnotes",
                            "table",
                        ],
                    )
                    occurrences["text"] = markdown(occurrence.resource_data.decode())
            case "image":
                occurrences["images"].append(
                    {
                        "title": occurrence.get_attribute_by_name("title").value,
                        "url": occurrence.resource_ref,
                    }
                )
            case "3d-scene":
                occurrences["3d-scenes"].append(
                    {
                        "title": occurrence.get_attribute_by_name("title").value,
                        "url": occurrence.resource_ref,
                    }
                )
            case "file":
                occurrences["files"].append(
                    {
                        "title": occurrence.get_attribute_by_name("title").value,
                        "url": occurrence.resource_ref,
                    }
                )
            case "url":
                occurrences["links"].append(
                    {
                        "title": occurrence.get_attribute_by_name("title").value,
                        "url": occurrence.resource_ref,
                    }
                )
            case "video":
                occurrences["videos"].append(
                    {
                        "title": occurrence.get_attribute_by_name("title").value,
                        "url": occurrence.resource_ref,
                    }
                )
            case "note" if occurrence.resource_data:
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
            case "temporal-event":
                occurrences["temporal-events"].append(
                    {
                        "identifier": occurrence.identifier,
                        "title": "Temporal Event",
                        "start_date": maya.parse(occurrence.get_attribute_by_name("timeline-start-date").value).date.strftime("%a, %d %b %Y"),
                        "text": occurrence.resource_data.decode(),
                    }
                )
            case "temporal-era":
                occurrences["temporal-eras"].append(
                    {
                        "identifier": occurrence.identifier,
                        "title": "Temporal Era",
                        "start_date": maya.parse(occurrence.get_attribute_by_name("timeline-start-date").value).date.strftime("%a, %d %b %Y"),
                        "end_date": maya.parse(occurrence.get_attribute_by_name("timeline-end-date").value).date.strftime("%a, %d %b %Y"),
                        "text": occurrence.resource_data.decode(),
                    }
                )
            case _:  # Unknown occurrence type
                abort(500)

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
    breadcrumbs = deque(session["breadcrumbs"], constants.BREADCRUMBS_COUNT)
    if topic_identifier in breadcrumbs:
        breadcrumbs.remove(topic_identifier)
    breadcrumbs.append(topic_identifier)
    session["breadcrumbs"] = list(breadcrumbs)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "topic/view.html",
        topic_map=topic_map,
        topic=topic,
        scope_filtered=scope_filtered,
        occurrences=occurrences,
        associations=associations,
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
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_topic_identifier = request.form.get("topic-identifier", "").strip()
        form_topic_name = request.form.get("topic-name", "").strip()
        form_topic_text = request.form.get("topic-text", "").strip()
        form_topic_instance_of = request.form.get("topic-instance-of", "").strip()
        form_topic_text_scope = request.form.get("topic-text-scope", "").strip()

        # Timeline-specific form data
        form_timeline_type = request.form.get("timeline-type")
        form_timeline_description = request.form.get("timeline-description", "").strip()
        form_timeline_media_url = request.form.get("timeline-media-url", "").strip()
        form_timeline_start = request.form.get("timeline-start-date", "").strip()
        form_timeline_end = request.form.get("timeline-end-date", "").strip()

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
        if form_timeline_type == "event":
            if not form_timeline_description:
                error = error | 32
            if not form_timeline_start:
                error = error | 64
        elif form_timeline_type == "era":
            if not form_timeline_start:
                error = error | 64
            if not form_timeline_end:
                error = error | 128

        if error != 0:
            flash(
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
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

            # Persist timeline-related objects to the topic store
            if form_timeline_type == "event":
                event_occurrence = Occurrence(
                    instance_of="temporal-event",
                    topic_identifier=new_topic.identifier,
                    scope=session["current_scope"],
                    resource_data=form_timeline_description,
                )
                start_date_attribute = Attribute(
                    "timeline-start-date",
                    form_timeline_start,
                    event_occurrence.identifier,
                    data_type=DataType.TIMESTAMP,
                )
                media_url_attribute = Attribute(
                    "timeline-media-url",
                    form_timeline_media_url,
                    event_occurrence.identifier,
                    data_type=DataType.STRING,
                )
                store.create_occurrence(topic_map.identifier, event_occurrence, ontology_mode=OntologyMode.LENIENT)
                store.create_attribute(topic_map.identifier, start_date_attribute)
                store.create_attribute(topic_map.identifier, media_url_attribute)
            elif form_timeline_type == "era":
                era_occurrence = Occurrence(
                    instance_of="temporal-era",
                    topic_identifier=new_topic.identifier,
                    scope=session["current_scope"],
                    resource_data=form_timeline_description,
                )
                start_date_attribute = Attribute(
                    "timeline-start-date",
                    form_timeline_start,
                    era_occurrence.identifier,
                    data_type=DataType.TIMESTAMP,
                )
                end_date_attribute = Attribute(
                    "timeline-end-date",
                    form_timeline_end,
                    era_occurrence.identifier,
                    data_type=DataType.TIMESTAMP,
                )
                store.create_occurrence(topic_map.identifier, era_occurrence, ontology_mode=OntologyMode.LENIENT)
                store.create_attribute(topic_map.identifier, start_date_attribute)
                store.create_attribute(topic_map.identifier, end_date_attribute)

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
        temporals_feature=constants.TEMPORALS_FEATURE,  # Toggle feature on or off
    )


@bp.route("/topics/edit/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def edit(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

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
        form_topic_name = request.form.get("topic-name", "").strip()
        form_topic_text = request.form.get("topic-text", "").strip()
        form_topic_instance_of = request.form.get("topic-instance-of", "").strip()
        form_topic_text_scope = request.form.get("topic-text-scope", "").strip()

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
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
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


@bp.route("/topics/delete/<map_identifier>/<topic_identifier>", methods=("POST",))
@login_required
def delete(map_identifier, topic_identifier):
    store, topic_map, _ = initialize(map_identifier, topic_identifier, current_user)

    try:
        # Remove the topic from the topic store
        store.delete_topic(map_identifier, topic_identifier)

        # Clear the breadcrumbs (of which this topic was part of)
        session["breadcrumbs"] = []

        # TODO: Review
        # Remove the topic's resources directory
        # topic_directory = os.path.join(
        #     current_app.static_folder, constants.RESOURCES_DIRECTORY, str(map_identifier), topic_identifier
        # )
        # if os.path.isdir(topic_directory):
        #     shutil.rmtree(topic_directory)
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


@bp.route("/topics/add-note/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add_note(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_note_title = request.form.get("note-title", "").strip()
        form_note_text = request.form.get("note-text", "").strip()
        form_note_scope = request.form.get("note-scope", "").strip()

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
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
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
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

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
        form_note_title = request.form.get("note-title", "").strip()
        form_note_text = request.form.get("note-text", "").strip()
        form_note_scope = request.form.get("note-scope", "").strip()

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
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
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
    methods=("POST",),
)
@login_required
def delete_note(map_identifier, topic_identifier, note_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    error = 0

    note_occurrence = store.get_occurrence(
        map_identifier,
        note_identifier,
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if not note_occurrence:
        error = error | 1

    if error != 0:
        flash("An error occurred while trying to delete the note.", "warning")
    else:
        try:
            store.delete_occurrence(map_identifier, note_occurrence.identifier)
            flash("Note successfully deleted.", "success")
        except TopicDbError:
            flash(
                "An error occurred while trying to delete the note. The note was not deleted.",
                "warning",
            )
    return redirect(
        url_for(
            "topic.view",
            map_identifier=topic_map.identifier,
            topic_identifier=topic.identifier,
        )
    )


@bp.route("/topics/view-names/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def view_names(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

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
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_topic_name = request.form.get("topic-name", "").strip()
        form_topic_name_scope = request.form.get("topic-name-scope", "").strip()

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
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
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
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    form_topic_name = topic.get_base_name(name_identifier).name
    form_topic_name_scope = topic.get_base_name(name_identifier).scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_topic_name = request.form.get("topic-name", "").strip()
        form_topic_name_scope = request.form.get("topic-name-scope", "").strip()

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
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
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
    methods=("POST",),
)
@login_required
def delete_name(map_identifier, topic_identifier, name_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    error = 0

    topic_name = topic.get_base_name(name_identifier).name

    if not topic_name:
        error = error | 1

    if error != 0:
        flash("An error occurred while trying to delete the topic name.", "warning")
    else:
        try:
            store.delete_base_name(map_identifier, name_identifier)
            flash("Topic name successfully deleted.", "success")
        except TopicDbError:
            flash(
                "An error occurred while trying to delete the topic name. The name was not deleted.",
                "warning",
            )
    return redirect(
        url_for(
            "topic.view_names",
            map_identifier=topic_map.identifier,
            topic_identifier=topic.identifier,
        )
    )


@bp.route("/topics/change-scope/<map_identifier>/<topic_identifier>", methods=("POST",))
@login_required
def change_scope(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    form_scope = request.form.get("scope-identifier", "").strip().lower()
    error = 0

    # If no values have been provided set their default values
    if not form_scope:
        form_scope = constants.UNIVERSAL_SCOPE

    # Validate form inputs
    if not store.topic_exists(topic_map.identifier, form_scope):
        error = error | 1

    if error != 0:
        flash(
            "You provided a scope identifier that does not exist. The active scope was left unchanged.",
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


@bp.route(
    "/topics/edit-identifier/<map_identifier>/<topic_identifier>",
    methods=("GET", "POST"),
)
@login_required
def edit_identifier(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    form_topic_identifier = topic.identifier
    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_topic_identifier = request.form.get("topic-identifier", "").strip()

        # Validate form inputs
        if not form_topic_identifier:
            error = error | 1
        if store.topic_exists(topic_map.identifier, form_topic_identifier):
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
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


@bp.route("/topics/index/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
def index(map_identifier, topic_identifier):
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

    if request.method == "POST":
        topics_filtered = request.form.get("topic-filtered") == "on"
    else:
        # Base-topics filtering, initially, can be in one of three states:
        #   - Unspecified (None)
        #   - Not on (off)
        #   - On

        # Determine if (active) filtering has been specified in either the URL or, previously,
        # in the session. If filtering is undefined then set it to be on.
        topics_filtered = request.args.get("filter", type=int)
        if topics_filtered is None:
            topics_filtered = session.get("topics_filtered", default="on")

    session["topics_filtered"] = topics_filtered

    # Pagination
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * constants.TOPIC_ITEMS_PER_PAGE

    if topics_filtered:
        topics_count = store.get_topics_count(map_identifier, RetrievalMode.FILTER_BASE_TOPICS)
        topics = store.get_topics(
            map_identifier,
            offset=offset,
            limit=constants.TOPIC_ITEMS_PER_PAGE,
            filter_base_topics=RetrievalMode.FILTER_BASE_TOPICS,
        )
    else:
        topics_count = store.get_topics_count(map_identifier)
        topics = store.get_topics(map_identifier, offset=offset, limit=constants.TOPIC_ITEMS_PER_PAGE)

    # Pagination
    total_pages = (topics_count + constants.TOPIC_ITEMS_PER_PAGE - 1) // constants.TOPIC_ITEMS_PER_PAGE

    return render_template(
        "topic/index.html",
        topic_map=topic_map,
        topic=topic,
        topics=topics,
        page=page,
        total_pages=total_pages,
        topics_filtered=topics_filtered,
    )
