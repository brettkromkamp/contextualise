"""
link.py file. Part of the Contextualise project.

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

bp = Blueprint("link", __name__)


@bp.route("/links/<map_identifier>/<topic_identifier>")
@login_required
def index(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    link_occurrences = store.get_topic_occurrences(
        map_identifier,
        topic_identifier,
        "url",
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    links = []
    for link_occurrence in link_occurrences:
        links.append(
            {
                "identifier": link_occurrence.identifier,
                "title": link_occurrence.get_attribute_by_name("title").value,
                "scope": link_occurrence.scope,
                "url": link_occurrence.resource_ref,
            }
        )

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "link/index.html",
        topic_map=topic_map,
        topic=topic,
        links=links,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/links/add/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_link_title = request.form.get("link-title", "").strip()
        form_link_url = request.form.get("link-url", "").strip()
        form_link_scope = request.form.get("link-scope", "").strip()

        # If no values have been provided set their default values
        if not form_link_scope:
            form_link_scope = session["current_scope"]

        # Validate form inputs
        if not form_link_title:
            error = error | 1
        if not form_link_url:
            error = error | 2
        if not store.topic_exists(topic_map.identifier, form_link_scope):
            error = error | 4

        if error != 0:
            flash(
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
                "warning",
            )
        else:
            link_occurrence = Occurrence(
                instance_of="url",
                topic_identifier=topic.identifier,
                scope=form_link_scope,
                resource_ref=form_link_url,
            )
            title_attribute = Attribute(
                "title",
                form_link_title,
                link_occurrence.identifier,
                data_type=DataType.STRING,
            )

            # Persist objects to the topic store
            store.create_occurrence(topic_map.identifier, link_occurrence)
            store.create_attribute(topic_map.identifier, title_attribute)

            flash("Link successfully added.", "success")
            return redirect(
                url_for(
                    "link.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

        return render_template(
            "link/add.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            link_title=form_link_title,
            link_url=form_link_url,
            link_scope=form_link_scope,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "link/add.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route("/links/edit/<map_identifier>/<topic_identifier>/<link_identifier>", methods=("GET", "POST"))
@login_required
def edit(map_identifier, topic_identifier, link_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    link_occurrence = store.get_occurrence(
        map_identifier,
        link_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    form_link_title = link_occurrence.get_attribute_by_name("title").value
    form_link_scope = link_occurrence.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_link_title = request.form.get("link-title", "").strip()
        form_link_scope = request.form.get("link-scope", "").strip()

        # If no values have been provided set their default values
        if not form_link_scope:
            form_link_scope = session["current_scope"]

        # Validate form inputs
        if not form_link_title:
            error = error | 1
        if not store.topic_exists(topic_map.identifier, form_link_scope):
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
                "warning",
            )
        else:
            # Update link's title if it has changed
            if link_occurrence.get_attribute_by_name("title").value != form_link_title:
                store.update_attribute_value(
                    topic_map.identifier,
                    link_occurrence.get_attribute_by_name("title").identifier,
                    form_link_title,
                )

            # Update link's scope if it has changed
            if link_occurrence.scope != form_link_scope:
                store.update_occurrence_scope(map_identifier, link_occurrence.identifier, form_link_scope)

            flash("Link successfully updated.", "success")
            return redirect(
                url_for(
                    "link.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    return render_template(
        "link/edit.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        link_identifier=link_occurrence.identifier,
        link_title=form_link_title,
        link_scope=form_link_scope,
        map_notes_count=map_notes_count,
    )


@bp.route("/links/delete/<map_identifier>/<topic_identifier>/<link_identifier>", methods=("POST",))
@login_required
def delete(map_identifier, topic_identifier, link_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    error = 0

    link_occurrence = store.get_occurrence(
        map_identifier,
        link_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if not link_occurrence:
        error = error | 1

    if error != 0:
        flash("An error occurred while trying to delete the link.", "warning")
    else:
        try:
            # Delete link occurrence from topic store
            store.delete_occurrence(map_identifier, link_occurrence.identifier)
            flash("Link successfully deleted.", "success")
        except TopicDbError:
            flash(
                "An error occurred while trying to delete the link. The link was not deleted.",
                "warning",
            )

    return redirect(
        url_for(
            "link.index",
            map_identifier=topic_map.identifier,
            topic_identifier=topic.identifier,
        )
    )
