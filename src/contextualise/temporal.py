"""
temporal.py file. Part of the Contextualise project.

November 7, 2024
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import re
from datetime import datetime

import maya  # type: ignore
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required  # type: ignore
from topicdb.models.attribute import Attribute
from topicdb.models.datatype import DataType
from topicdb.models.occurrence import Occurrence
from topicdb.store.ontologymode import OntologyMode
from topicdb.store.retrievalmode import RetrievalMode
from topicdb.topicdberror import TopicDbError

from contextualise.temporaltype import TemporalType
from contextualise.utilities.topicstore import initialize

bp = Blueprint("temporal", __name__)


# region Functions
def _validate_date(date_string: str) -> bool:
    """
    Validate a date string using regex for format and datetime for strict validation.
    :param date_string: The input date string in 'yyyy-mm-dd' format.
    :return: True if valid, False otherwise.
    """
    # Regex pattern for yyyy-mm-dd
    date_regex = r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"

    # Step 1: Check the format using regex
    if not re.match(date_regex, date_string):
        return False

    # Step 2: Strict validation using datetime
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# endregion


@bp.route("/temporals/<map_identifier>/<topic_identifier>")
@login_required
def index(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    temporal_type = TemporalType.EVENT
    temporal_occurrences = store.get_topic_occurrences(
        map_identifier,
        topic_identifier,
        "temporal-event",
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if not temporal_occurrences:
        temporal_type = TemporalType.ERA
        temporal_occurrences = store.get_topic_occurrences(
            map_identifier,
            topic_identifier,
            "temporal-era",
            inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )

    temporals = []
    for temporal_occurrence in temporal_occurrences:
        temporal_end_date = (
            temporal_occurrence.get_attribute_by_name("temporal-end-date").value
            if temporal_type is TemporalType.ERA
            else None
        )
        temporal_end_date_view = ""
        if temporal_end_date:
            temporal_end_date_view = maya.parse(temporal_end_date).date.strftime("%a, %d %b %Y")
        temporals.append(
            {
                "identifier": temporal_occurrence.identifier,
                "topic_identifier": temporal_occurrence.topic_identifier,
                "type": temporal_type.name.lower(),
                "start_date": temporal_occurrence.get_attribute_by_name("temporal-start-date").value,
                "start_date_view": maya.parse(
                    temporal_occurrence.get_attribute_by_name("temporal-start-date").value
                ).date.strftime("%a, %d %b %Y"),
                "end_date": temporal_occurrence.get_attribute_by_name("temporal-end-date").value
                if temporal_type is TemporalType.ERA
                else None,
                "end_date_view": temporal_end_date_view,
                "description": temporal_occurrence.resource_data.decode("utf-8")
                if temporal_occurrence.has_data
                else None,
                "scope": temporal_occurrence.scope,
            }
        )

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "temporal/index.html",
        topic_map=topic_map,
        topic=topic,
        temporals=temporals,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/temporals/add/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    temporals = store.get_topic_occurrences(
        map_identifier=map_identifier,
        identifier=topic_identifier,
        instance_of="temporal-event",
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    ) + store.get_topic_occurrences(
        map_identifier=map_identifier,
        identifier=topic_identifier,
        instance_of="temporal-era",
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    temporal = temporals[0] if len(temporals) > 0 else None

    if request.method == "POST":
        form_temporal_event = request.form.get("temporal-type")
        form_temporal_description = request.form.get("temporal-description", "").strip()
        form_temporal_media_url = request.form.get("temporal-media-url", "").strip()
        form_temporal_start_date = request.form.get("temporal-start-date", "").strip()
        form_temporal_end_date = request.form.get("temporal-end-date", "").strip()
        form_temporal_scope = request.form.get("temporal-scope", "").strip()

        # If no values have been provided set their default values
        if not form_temporal_scope:
            form_temporal_scope = session["current_scope"]

        temporal_type = TemporalType.EVENT if form_temporal_event == "event" else TemporalType.ERA

        # Validate form inputs
        if not form_temporal_description:
            error = error | 1
        if not form_temporal_start_date:
            error = error | 2
        if not _validate_date(form_temporal_start_date):
            error = error | 4
        if temporal_type == TemporalType.ERA:
            if not form_temporal_end_date:
                error = error | 8
            if not _validate_date(form_temporal_end_date):
                error = error | 16

        if error != 0:
            flash(
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
                "warning",
            )
        else:
            # Persist objects to the topic store
            match temporal_type:
                case TemporalType.EVENT:
                    event_occurrence = Occurrence(
                        instance_of="temporal-event",
                        topic_identifier=topic_identifier,
                        scope=form_temporal_scope,
                        resource_data=form_temporal_description,
                    )
                    start_date_attribute = Attribute(
                        "temporal-start-date",
                        form_temporal_start_date,
                        event_occurrence.identifier,
                        data_type=DataType.TIMESTAMP,
                    )
                    store.create_occurrence(topic_map.identifier, event_occurrence, ontology_mode=OntologyMode.LENIENT)
                    store.create_attribute(topic_map.identifier, start_date_attribute)

                    if form_temporal_media_url:
                        media_url_attribute = Attribute(
                            "temporal-media-url",
                            form_temporal_media_url,
                            event_occurrence.identifier,
                            data_type=DataType.STRING,
                        )
                        store.create_attribute(topic_map.identifier, media_url_attribute)
                case TemporalType.ERA:
                    era_occurrence = Occurrence(
                        instance_of="temporal-era",
                        topic_identifier=topic_identifier,
                        scope=form_temporal_scope,
                        resource_data=form_temporal_description,
                    )
                    start_date_attribute = Attribute(
                        "temporal-start-date",
                        form_temporal_start_date,
                        era_occurrence.identifier,
                        data_type=DataType.TIMESTAMP,
                    )
                    end_date_attribute = Attribute(
                        "temporal-end-date",
                        form_temporal_end_date,
                        era_occurrence.identifier,
                        data_type=DataType.TIMESTAMP,
                    )
                    store.create_occurrence(topic_map.identifier, era_occurrence, ontology_mode=OntologyMode.LENIENT)
                    store.create_attribute(topic_map.identifier, start_date_attribute)
                    store.create_attribute(topic_map.identifier, end_date_attribute)

            flash("Temporal successfully added.", "success")
            return redirect(
                url_for(
                    "temporal.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )

        return render_template(
            "temporal/add.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            temporal=temporal,
            temporal_topic_identifier=topic_identifier,
            temporal_type=form_temporal_event,
            temporal_description=form_temporal_description,
            temporal_media_url=form_temporal_media_url,
            temporal_start_date=form_temporal_start_date,
            temporal_end_date=form_temporal_end_date,
            temporal_scope=form_temporal_scope,
            map_notes_count=map_notes_count,
        )

    if temporal:
        temporal_type = TemporalType.ERA if temporal.instance_of == "temporal-era" else TemporalType.EVENT
        temporal_description = temporal.resource_data.decode("utf-8") if temporal.has_data else None
        temporal_media_url = (
            temporal.get_attribute_by_name("temporal-media-url").value if temporal_type is TemporalType.EVENT else None
        )
        temporal_start_date = temporal.get_attribute_by_name("temporal-start-date").value
        temporal_end_date = (
            temporal.get_attribute_by_name("temporal-end-date").value if temporal_type is TemporalType.ERA else None
        )
        flash("This topic has already been defined as a temporal event or era.", "warning")
    return render_template(
        "temporal/add.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        temporal=temporal,
        temporal_topic_identifier=temporal.topic_identifier if temporal else None,
        temporal_type=temporal_type.name.lower() if temporal else None,
        temporal_description=temporal_description if temporal else None,
        temporal_media_url=temporal_media_url if temporal else None,
        temporal_start_date=temporal_start_date if temporal else None,
        temporal_end_date=temporal_end_date if temporal else None,
        temporal_scope=temporal.scope if temporal else None,
        map_notes_count=map_notes_count,
    )


@bp.route("/temporals/edit/<map_identifier>/<topic_identifier>/<temporal_identifier>", methods=("GET", "POST"))
@login_required
def edit(map_identifier, topic_identifier, temporal_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    if request.method == "POST":
        pass

    return render_template(
        "temporal/edit.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        temporal_identifier=temporal_identifier,
        map_notes_count=map_notes_count,
    )


@bp.route("/temporals/delete/<map_identifier>/<topic_identifier>/<temporal_identifier>", methods=("POST",))
@login_required
def delete(map_identifier, topic_identifier, temporal_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    error = 0

    temporal_occurrence = store.get_occurrence(
        map_identifier,
        temporal_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if not temporal_occurrence:
        error = error | 1

    if error != 0:
        flash("An error occurred while trying to delete the temporal.", "warning")
    else:
        try:
            # Delete temporal occurrence from topic store
            store.delete_occurrence(map_identifier, temporal_occurrence.identifier)
            flash("Temporal successfully deleted.", "success")
        except TopicDbError:
            flash(
                "An error occurred while trying to delete the temporal. The temporal was not deleted.",
                "warning",
            )

    return redirect(
        url_for(
            "temporal.index",
            map_identifier=topic_map.identifier,
            topic_identifier=topic.identifier,
        )
    )
