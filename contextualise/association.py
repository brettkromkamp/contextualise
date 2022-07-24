"""
association.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import maya
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_security import current_user, login_required
from topicdb.core.models.association import Association
from topicdb.core.models.collaborationmode import CollaborationMode
from topicdb.core.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint("association", __name__)

UNIVERSAL_SCOPE = "*"


@bp.route("/associations/<map_identifier>/<topic_identifier>")
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

    associations = store.get_topic_associations(map_identifier, topic_identifier)

    # occurrences_stats = store.get_topic_occurrences_statistics(map_identifier, topic_identifier)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "association/index.html",
        topic_map=topic_map,
        topic=topic,
        associations=associations,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/associations/create/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def create(map_identifier, topic_identifier):
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

    flash(
        "Take a look at this page to see practical examples of <a href='https://brettkromkamp.com/posts/semantically-meaningful-relationships/'>semantically meaningful relationships</a>.",
        "info",
    )

    if request.method == "POST":
        form_association_dest_topic_ref = request.form["association-dest-topic-ref"].strip()
        form_association_dest_role_spec = request.form["association-dest-role-spec"].strip()
        form_association_src_topic_ref = topic_identifier
        form_association_src_role_spec = request.form["association-src-role-spec"].strip()
        form_association_instance_of = request.form["association-instance-of"].strip()
        form_association_scope = request.form["association-scope"].strip()
        form_association_name = request.form["association-name"].strip()
        form_association_identifier = request.form["association-identifier"].strip()

        # If no values have been provided set their default values
        if not form_association_dest_role_spec:
            form_association_dest_role_spec = "related"
        if not form_association_src_role_spec:
            form_association_src_role_spec = "related"
        if not form_association_instance_of:
            form_association_instance_of = "association"
        if not form_association_scope:
            form_association_scope = session["current_scope"]
        if not form_association_name:
            form_association_name = "Undefined"
        if not form_association_identifier:
            form_association_identifier = ""

        # Validate form inputs
        if not store.topic_exists(topic_map.identifier, form_association_dest_topic_ref):
            error = error | 1
        if form_association_dest_role_spec != "related" and not store.topic_exists(
            topic_map.identifier, form_association_dest_role_spec
        ):
            error = error | 2
        if form_association_src_role_spec != "related" and not store.topic_exists(
            topic_map.identifier, form_association_src_role_spec
        ):
            error = error | 4
        if form_association_instance_of != "association" and not store.topic_exists(
            topic_map.identifier, form_association_instance_of
        ):
            error = error | 8
        if form_association_scope != UNIVERSAL_SCOPE and not store.topic_exists(
            topic_map.identifier, form_association_scope
        ):
            error = error | 16
        if form_association_identifier and store.topic_exists(topic_map.identifier, form_association_identifier):
            error = error | 32

        # TODO: Flag an error to prevent the user from creating an association with the reserved
        # 'navigation' or 'categorization' types

        # If role identifier topics are missing then create them
        if error & 2:  # Destination role spec
            pass
        if error & 4:  # Source role spec
            pass

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            association = Association(
                identifier=form_association_identifier,
                instance_of=form_association_instance_of,
                name=form_association_name,
                scope=form_association_scope,
                src_topic_ref=form_association_src_topic_ref,
                src_role_spec=form_association_src_role_spec,
                dest_topic_ref=form_association_dest_topic_ref,
                dest_role_spec=form_association_dest_role_spec,
            )

            # Persist association object to the topic store
            store.create_association(map_identifier, association)

            flash("Association successfully created.", "success")
            return redirect(
                url_for(
                    "association.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic_identifier,
                )
            )

        return render_template(
            "association/create.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            association_instance_of=form_association_instance_of,
            association_src_topic_ref=form_association_src_topic_ref,
            association_src_role_spec=form_association_src_role_spec,
            association_dest_topic_ref=form_association_dest_topic_ref,
            association_dest_role_spec=form_association_dest_role_spec,
            association_scope=form_association_scope,
            association_name=form_association_name,
            association_identifier=form_association_identifier,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "association/create.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/associations/delete/<map_identifier>/<topic_identifier>/<association_identifier>",
    methods=("GET", "POST"),
)
@login_required
def delete(map_identifier, topic_identifier, association_identifier):
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

    association = store.get_association(map_identifier, association_identifier)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    if request.method == "POST":
        store.delete_association(map_identifier, association_identifier)
        flash("Association successfully deleted.", "warning")
        return redirect(
            url_for(
                "association.index",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
            )
        )

    return render_template(
        "association/delete.html",
        topic_map=topic_map,
        topic=topic,
        association=association,
        map_notes_count=map_notes_count,
    )


@bp.route("/associations/view/<map_identifier>/<topic_identifier>/<association_identifier>")
@login_required
def view(map_identifier, topic_identifier, association_identifier):
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

    association = store.get_association(map_identifier, association_identifier)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "association/view.html",
        topic_map=topic_map,
        topic=topic,
        association=association,
        map_notes_count=map_notes_count,
    )
