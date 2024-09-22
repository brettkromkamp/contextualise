"""
association.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import maya
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_security import current_user, login_required
from topicdb.models.association import Association
from topicdb.topicdberror import TopicDbError
from werkzeug.exceptions import abort

from contextualise.utilities.topicstore import initialize

from . import constants

bp = Blueprint("association", __name__)


@bp.route("/associations/<map_identifier>/<topic_identifier>")
@login_required
def index(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    associations = store.get_topic_associations(map_identifier, topic_identifier)

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
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    flash(
        "Take a look at this page to see practical examples of <a href='https://brettkromkamp.com/posts/semantically-meaningful-relationships/'>semantically meaningful relationships</a>.",
        "info",
    )

    if request.method == "POST":
        form_association_dest_topic_ref = request.form.get("association-dest-topic-ref", "").strip()
        form_association_dest_role_spec = request.get("association-dest-role-spec", "").strip()
        form_association_src_topic_ref = topic_identifier
        form_association_src_role_spec = request.get("association-src-role-spec", "").strip()
        form_association_instance_of = request.form.get("association-instance-of", "").strip()
        form_association_scope = request.form.get("association-scope", "").strip()
        form_association_name = request.form.get("association-name", "").strip()
        form_association_identifier = request.form.get("association-identifier", "").strip()

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
        if form_association_scope != constants.UNIVERSAL_SCOPE and not store.topic_exists(
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
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
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


@bp.route("/associations/delete/<map_identifier>/<topic_identifier>/<association_identifier>", methods=("POST",))
@login_required
def delete(map_identifier, topic_identifier, association_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    error = 0

    association = store.get_association(map_identifier, association_identifier)

    if not association:
        error = error | 1

    if error != 0:
        flash("An error occurred while trying to delete the association.", "warning")
    else:
        try:
            store.delete_association(map_identifier, association_identifier)
            flash("Association successfully deleted.", "success")
        except TopicDbError:
            flash(
                "An error occurred while trying to delete the association. The association was not deleted.",
                "warning",
            )

    return redirect(
        url_for(
            "association.index",
            map_identifier=topic_map.identifier,
            topic_identifier=topic.identifier,
        )
    )


@bp.route("/associations/view/<map_identifier>/<topic_identifier>/<association_identifier>")
@login_required
def view(map_identifier, topic_identifier, association_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    association = store.get_association(map_identifier, association_identifier)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "association/view.html",
        topic_map=topic_map,
        topic=topic,
        association=association,
        map_notes_count=map_notes_count,
    )
