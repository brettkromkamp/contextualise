"""
attribute.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import maya
from flask import Blueprint, flash, render_template, request, session, url_for
from flask_login import current_user
from flask_security import login_required
from topicdb.models.attribute import Attribute
from topicdb.models.datatype import DataType
from topicdb.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from contextualise.utilities.topicstore import initialize

bp = Blueprint("attribute", __name__)


@bp.route("/attributes/<map_identifier>/<topic_identifier>")
@login_required
def index(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    attributes = []
    entity_attributes = store.get_attributes(map_identifier, topic_identifier)

    for entity_attribute in entity_attributes:
        attributes.append(
            {
                "identifier": entity_attribute.identifier,
                "name": entity_attribute.name,
                "value": entity_attribute.value,
                "type": str(entity_attribute.data_type).lower(),
                "scope": entity_attribute.scope,
            }
        )

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    entity_type = "topic"
    return_url = "topic.view"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "attribute/index.html",
        topic_map=topic_map,
        topic=topic,
        entity_type=entity_type,
        return_url=return_url,
        attributes=attributes,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/attributes/<map_identifier>/<topic_identifier>/<entity_identifier>/<entity_type>")
@login_required
def entity_index(map_identifier, topic_identifier, entity_identifier, entity_type):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    entity = store.get_association(
        map_identifier,
        entity_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if entity is None:
        entity = store.get_occurrence(map_identifier, entity_identifier)

    if entity is None:
        abort(404)

    return_urls = {
        "association": "association.index",
        "image": "image.index",
        "3d-scene": "three_d.index",
        "file": "file.index",
        "link": "link.index",
        "video": "video.index",
        "temporal": "temporal.index",
    }
    return_url = return_urls.get(entity_type, "image.view")  # Default to image.view. Should it be like this?

    attributes = []
    entity_attributes = store.get_attributes(map_identifier, entity_identifier)

    for entity_attribute in entity_attributes:
        attributes.append(
            {
                "identifier": entity_attribute.identifier,
                "name": entity_attribute.name,
                "value": entity_attribute.value,
                "type": str(entity_attribute.data_type).lower(),
                "scope": entity_attribute.scope,
            }
        )

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "attribute/index.html",
        topic_map=topic_map,
        topic=topic,
        entity=entity,
        entity_type=entity_type,
        return_url=return_url,
        attributes=attributes,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/attributes/add/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    entity_type = "topic"
    post_url = "attribute.add"
    cancel_url = "attribute.index"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_attribute_name = request.form.get("attribute-name", "").strip()
        form_attribute_value = request.form.get("attribute-value", "").strip()
        form_attribute_type = request.form.get("attribute-type")
        form_attribute_scope = request.form.get("attribute-scope", "").strip()

        # If no values have been provided set their default values
        if not form_attribute_scope:
            form_attribute_scope = session["current_scope"]

        # Validate form inputs
        if not form_attribute_name:
            error = error | 1
        if not form_attribute_value:
            error = error | 2
        if not store.topic_exists(topic_map.identifier, form_attribute_scope):
            error = error | 4
        if topic.get_attribute_by_name(form_attribute_name):
            error = error | 8

        if error != 0:
            flash(
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
                "warning",
            )
        else:
            attribute = Attribute(
                form_attribute_name,
                form_attribute_value,
                topic.identifier,
                data_type=DataType[form_attribute_type],
                scope=form_attribute_scope,
            )

            # Persist objects to the topic store
            store.create_attribute(topic_map.identifier, attribute)

            flash("Attribute successfully added.", "success")
            return redirect(
                url_for(
                    "attribute.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

        return render_template(
            "attribute/add.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            entity_type=entity_type,
            post_url=post_url,
            cancel_url=cancel_url,
            attribute_name=form_attribute_name,
            attribute_value=form_attribute_value,
            attribute_type=form_attribute_type,
            attribute_scope=form_attribute_scope,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "attribute/add.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        entity_type=entity_type,
        post_url=post_url,
        cancel_url=cancel_url,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/attributes/add/<map_identifier>/<topic_identifier>/<entity_identifier>/<entity_type>",
    methods=("GET", "POST"),
)
@login_required
def entity_add(map_identifier, topic_identifier, entity_identifier, entity_type):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    entity = store.get_occurrence(
        map_identifier,
        entity_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if entity is None:
        abort(404)

    post_url = "attribute.entity_add"
    cancel_url = "attribute.entity_index"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_attribute_name = request.form.get("attribute-name", "").strip()
        form_attribute_value = request.form.get("attribute-value", "").strip()
        form_attribute_type = request.form.get("attribute-type")
        form_attribute_scope = request.form.get("attribute-scope", "").strip()

        # If no values have been provided set their default values
        if not form_attribute_scope:
            form_attribute_scope = session["current_scope"]

        # Validate form inputs
        if not form_attribute_name:
            error = error | 1
        if not form_attribute_value:
            error = error | 2
        if not store.topic_exists(topic_map.identifier, form_attribute_scope):
            error = error | 4
        if entity.get_attribute_by_name(form_attribute_name):
            error = error | 8

        if error != 0:
            flash(
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
                "warning",
            )
        else:
            attribute = Attribute(
                form_attribute_name,
                form_attribute_value,
                entity.identifier,
                data_type=DataType[form_attribute_type],
                scope=form_attribute_scope,
            )

            # Persist objects to the topic store
            store.create_attribute(topic_map.identifier, attribute)

            flash("Attribute successfully added.", "success")
            return redirect(
                url_for(
                    "attribute.entity_index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                    entity_identifier=entity.identifier,
                    entity_type=entity_type,
                )
            )

        return render_template(
            "attribute/add.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            entity=entity,
            entity_type=entity_type,
            post_url=post_url,
            cancel_url=cancel_url,
            attribute_name=form_attribute_name,
            attribute_value=form_attribute_value,
            attribute_type=form_attribute_type,
            attribute_scope=form_attribute_scope,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "attribute/add.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        entity=entity,
        entity_type=entity_type,
        post_url=post_url,
        cancel_url=cancel_url,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/attributes/edit/<map_identifier>/<topic_identifier>/<attribute_identifier>",
    methods=("GET", "POST"),
)
@login_required
def edit(map_identifier, topic_identifier, attribute_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    attribute = topic.get_attribute(attribute_identifier)
    if attribute is None:
        abort(404)

    form_attribute_name = attribute.name
    form_attribute_value = attribute.value
    form_attribute_type = str(attribute.data_type).capitalize()
    form_attribute_scope = attribute.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_attribute_name = request.form.get("attribute-name", "").strip()
        form_attribute_value = request.form.get("attribute-value", "").strip()
        form_attribute_type = request.form.get("attribute-type")
        form_attribute_scope = request.form.get("attribute-scope", "").strip()

        # If no values have been provided set their default values
        if not form_attribute_scope:
            form_attribute_scope = session["current_scope"]

        # Validate form inputs
        if not form_attribute_name:
            error = error | 1
        if not form_attribute_value:
            error = error | 2
        if not store.topic_exists(topic_map.identifier, form_attribute_scope):
            error = error | 4

        if error != 0:
            flash(
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
                "warning",
            )
        else:
            # Update the attribute by deleting the existing attribute and
            # adding a new one
            store.delete_attribute(map_identifier, attribute.identifier)
            updated_attribute = Attribute(
                form_attribute_name,
                form_attribute_value,
                topic.identifier,
                data_type=DataType[form_attribute_type],
                scope=form_attribute_scope,
            )
            store.create_attribute(topic_map.identifier, updated_attribute)

            flash("Attribute successfully updated.", "success")
            return redirect(
                url_for(
                    "attribute.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

    entity_type = "topic"
    data_types = [
        ("STRING", "String"),
        ("NUMBER", "Number"),
        ("TIMESTAMP", "Timestamp"),
        ("BOOLEAN", "Boolean"),
    ]
    post_url = "attribute.edit"
    cancel_url = "attribute.index"

    return render_template(
        "attribute/edit.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        attribute=attribute,
        entity_type=entity_type,
        data_types=data_types,
        post_url=post_url,
        cancel_url=cancel_url,
        attribute_name=form_attribute_name,
        attribute_value=form_attribute_value,
        attribute_type=form_attribute_type,
        attribute_scope=form_attribute_scope,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/attributes/edit/<map_identifier>/<topic_identifier>/<entity_identifier>/<attribute_identifier>/<entity_type>",
    methods=("GET", "POST"),
)
@login_required
def entity_edit(
    map_identifier,
    topic_identifier,
    entity_identifier,
    attribute_identifier,
    entity_type,
):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    if entity_type == "association":
        entity = store.get_association(
            map_identifier,
            entity_identifier,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )
    else:
        entity = store.get_occurrence(
            map_identifier,
            entity_identifier,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )
    if entity is None:
        abort(404)

    attribute = entity.get_attribute(attribute_identifier)
    if attribute is None:
        abort(404)

    form_attribute_name = attribute.name
    form_attribute_value = attribute.value
    form_attribute_type = str(attribute.data_type).capitalize()
    form_attribute_scope = attribute.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        form_attribute_name = request.form.get("attribute-name", "").strip()
        form_attribute_value = request.form.get("attribute-value", "").strip()
        form_attribute_type = request.form.get("attribute-type")
        form_attribute_scope = request.form.get("attribute-scope", "").strip()

        # If no values have been provided set their default values
        if not form_attribute_scope:
            form_attribute_scope = session["current_scope"]

        # Validate form inputs
        if not form_attribute_name:
            error = error | 1
        if not form_attribute_value:
            error = error | 2
        if not store.topic_exists(topic_map.identifier, form_attribute_scope):
            error = error | 4

        if error != 0:
            flash(
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
                "warning",
            )
        else:
            # Update the attribute by deleting the existing attribute and
            # adding a new one
            store.delete_attribute(map_identifier, attribute.identifier)
            updated_attribute = Attribute(
                form_attribute_name,
                form_attribute_value,
                entity.identifier,
                data_type=DataType[form_attribute_type],
                scope=form_attribute_scope,
            )
            store.create_attribute(topic_map.identifier, updated_attribute)

            flash("Attribute successfully updated.", "success")
            return redirect(
                url_for(
                    "attribute.entity_index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                    entity_identifier=entity.identifier,
                    entity_type=entity_type,
                )
            )

    data_types = [
        ("STRING", "String"),
        ("NUMBER", "Number"),
        ("TIMESTAMP", "Timestamp"),
        ("BOOLEAN", "Boolean"),
    ]
    post_url = "attribute.entity_edit"
    cancel_url = "attribute.entity_index"

    return render_template(
        "attribute/edit.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        attribute=attribute,
        entity=entity,
        entity_type=entity_type,
        data_types=data_types,
        post_url=post_url,
        cancel_url=cancel_url,
        attribute_name=form_attribute_name,
        attribute_value=form_attribute_value,
        attribute_type=form_attribute_type,
        attribute_scope=form_attribute_scope,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/attributes/delete/<map_identifier>/<topic_identifier>/<attribute_identifier>",
    methods=("GET", "POST"),
)
@login_required
def delete(map_identifier, topic_identifier, attribute_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    attribute = topic.get_attribute(attribute_identifier)
    if attribute is None:
        abort(404)

    form_attribute_name = attribute.name
    form_attribute_value = attribute.value
    form_attribute_type = str(attribute.data_type).capitalize()
    form_attribute_scope = attribute.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    if request.method == "POST":
        # Delete attribute from topic store
        store.delete_attribute(map_identifier, attribute.identifier)

        flash("Attribute successfully deleted.", "success")
        return redirect(
            url_for(
                "attribute.index",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
            )
        )

    entity_type = "topic"
    post_url = "attribute.delete"
    cancel_url = "attribute.index"

    return render_template(
        "attribute/delete.html",
        topic_map=topic_map,
        topic=topic,
        attribute=attribute,
        entity_type=entity_type,
        post_url=post_url,
        cancel_url=cancel_url,
        attribute_name=form_attribute_name,
        attribute_value=form_attribute_value,
        attribute_type=form_attribute_type,
        attribute_scope=form_attribute_scope,
        map_notes_count=map_notes_count,
    )


@bp.route(
    "/attributes/delete/<map_identifier>/<topic_identifier>/<entity_identifier>/<attribute_identifier>/<entity_type>",
    methods=("GET", "POST"),
)
@login_required
def entity_delete(
    map_identifier,
    topic_identifier,
    entity_identifier,
    attribute_identifier,
    entity_type,
):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    if entity_type == "association":
        entity = store.get_association(
            map_identifier,
            entity_identifier,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )
    else:
        entity = store.get_occurrence(
            map_identifier,
            entity_identifier,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )
    if entity is None:
        abort(404)

    attribute = entity.get_attribute(attribute_identifier)
    if attribute is None:
        abort(404)

    form_attribute_name = attribute.name
    form_attribute_value = attribute.value
    form_attribute_type = str(attribute.data_type).capitalize()
    form_attribute_scope = attribute.scope

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    if request.method == "POST":
        # Delete attribute from topic store
        store.delete_attribute(map_identifier, attribute.identifier)

        flash("Attribute successfully deleted.", "success")
        return redirect(
            url_for(
                "attribute.entity_index",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
                entity_identifier=entity.identifier,
                entity_type=entity_type,
            )
        )

    post_url = "attribute.entity_delete"
    cancel_url = "attribute.entity_index"

    return render_template(
        "attribute/delete.html",
        topic_map=topic_map,
        topic=topic,
        entity=entity,
        attribute=attribute,
        entity_type=entity_type,
        post_url=post_url,
        cancel_url=cancel_url,
        attribute_name=form_attribute_name,
        attribute_value=form_attribute_value,
        attribute_type=form_attribute_type,
        attribute_scope=form_attribute_scope,
        map_notes_count=map_notes_count,
    )
