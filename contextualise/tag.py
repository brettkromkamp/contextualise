"""
tag.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_security import current_user, login_required
from topicdb.core.models.collaborationmode import CollaborationMode
from topicdb.core.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint("tag", __name__)


@bp.route("/tags/add/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add(map_identifier, topic_identifier):
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

    form_tags = None

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_tags = request.form["topic-tags"].strip()

        # Validate form inputs
        if not form_tags:
            error = error | 1

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            for form_tag in form_tags.split(","):
                store.create_tag(map_identifier, topic.identifier, form_tag)

            flash("Tags successfully added.", "success")
            return redirect(
                url_for(
                    "topic.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    return render_template(
        "tag/add.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        topic_name=form_tags,
        map_notes_count=map_notes_count,
    )
