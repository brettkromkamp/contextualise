"""
temporal.py file. Part of the Contextualise project.

November 7, 2024
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from enum import Enum

import maya
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from flask_security import login_required
from topicdb.models.attribute import Attribute
from topicdb.models.datatype import DataType
from topicdb.models.occurrence import Occurrence
from topicdb.store.ontologymode import OntologyMode
from topicdb.store.retrievalmode import RetrievalMode
from topicdb.topicdberror import TopicDbError

from contextualise.utilities.topicstore import initialize

bp = Blueprint("temporal", __name__)

class TemporalType(Enum):
    EVENT = 1
    ERA = 2

    def __str__(self):
        return self.name.lower()


@bp.route("/temporals/<map_identifier>/<topic_identifier>")
@login_required
def index(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    temporal_type = "event"
    temporal_occurrences = store.get_topic_occurrences(
        map_identifier,
        topic_identifier,
        "temporal-event",
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if not temporal_occurrences:
        temporal_type = "era"
        temporal_occurrences = store.get_topic_occurrences(
            map_identifier,
            topic_identifier,
            "temporal-era",
            resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
        )

    temporals = []
    for temporal_occurrence in temporal_occurrences:
        temporals.append(
            {
                "identifier": temporal_occurrence.identifier,
                "topic_identifier": temporal_occurrence.topic_identifier,
                "type": temporal_type,
                "start_date": temporal_occurrence.get_attribute_by_name("temporal-start-date").value,
                "end_date": temporal_occurrence.get_attribute_by_name("temporal-end-date").value
                if temporal_type == "era"
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

    if request.method == "POST":
        form_temporal_type = request.form.get("temporal-type")
        form_temporal_description = request.form.get("temporal-description", "").strip()
        form_temporal_media_url = request.form.get("temporal-media-url", "").strip()
        form_temporal_start = request.form.get("temporal-start-date", "").strip()
        form_temporal_end = request.form.get("temporal-end-date", "").strip()
        form_temporal_scope = request.form.get("temporal-scope", "").strip()

        # If no values have been provided set their default values
        if not form_temporal_scope:
            form_temporal_scope = session["current_scope"]

        temporal_type = TemporalType.ERA if form_temporal_type == "on" else TemporalType.EVENT

        # Validate form inputs
        if not form_temporal_description:
            error = error | 1
        if not form_temporal_start:
            error = error | 2
        if temporal_type == TemporalType.EVENT:
            if not form_temporal_media_url:
                error = error | 4
        else:
            if not form_temporal_end:
                error = error | 8

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
                        scope=session["current_scope"],
                        resource_data=form_temporal_description,
                    )
                    start_date_attribute = Attribute(
                        "temporal-start-date",
                        form_temporal_start,
                        event_occurrence.identifier,
                        data_type=DataType.TIMESTAMP,
                    )
                    media_url_attribute = Attribute(
                        "temporal-media-url",
                        form_temporal_media_url,
                        event_occurrence.identifier,
                        data_type=DataType.STRING,
                    )
                    store.create_occurrence(topic_map.identifier, event_occurrence, ontology_mode=OntologyMode.LENIENT)
                    store.create_attribute(topic_map.identifier, start_date_attribute)
                    store.create_attribute(topic_map.identifier, media_url_attribute)
                case TemporalType.ERA:
                    era_occurrence = Occurrence(
                        instance_of="temporal-era",
                        topic_identifier=topic_identifier,
                        scope=session["current_scope"],
                        resource_data=form_temporal_description,
                    )
                    start_date_attribute = Attribute(
                        "temporal-start-date",
                        form_temporal_start,
                        era_occurrence.identifier,
                        data_type=DataType.TIMESTAMP,
                    )
                    end_date_attribute = Attribute(
                        "temporal-end-date",
                        form_temporal_end,
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
            temporal_type=form_temporal_type,
            temporal_description=form_temporal_description,
            temporal_media_url=form_temporal_media_url,
            temporal_start=form_temporal_start,
            temporal_end=form_temporal_end,
            temporal_scope=form_temporal_scope,
            map_notes_count=map_notes_count,
        )

    return render_template(
        "temporal/add.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route("/temporals/edit/<map_identifier>/<topic_identifier>/<temporal_identifier>", methods=("GET", "POST"))
@login_required
def edit(map_identifier, topic_identifier, temporal_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    if request.method == "POST":
        pass

    pass


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
