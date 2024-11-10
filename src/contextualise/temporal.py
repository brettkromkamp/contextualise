"""
temporal.py file. Part of the Contextualise project.

November 7, 2024
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import maya
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from flask_security import login_required
from topicdb.models.attribute import Attribute
from topicdb.models.datatype import DataType
from topicdb.models.occurrence import Occurrence
from topicdb.store.retrievalmode import RetrievalMode
from topicdb.topicdberror import TopicDbError

from contextualise.utilities.topicstore import initialize

bp = Blueprint("temporal", __name__)


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
                "end_date": temporal_occurrence.get_attribute_by_name("temporal-end-date").value if temporal_type == "era" else None,
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


@bp.route("/temporals/delete/<map_identifier>/<topic_identifier>/<link_identifier>", methods=("POST",))
@login_required
def delete(map_identifier, topic_identifier, link_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)
