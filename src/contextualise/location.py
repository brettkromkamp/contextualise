"""
location.py file. Part of the Contextualise project.

November 19, 2024
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import re
from datetime import datetime

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

from contextualise.temporaltype import TemporalType
from contextualise.utilities.topicstore import initialize

bp = Blueprint("location", __name__)

@bp.route("/locations/<map_identifier>/<topic_identifier>")
@login_required
def index(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "location/index.html",
        topic_map=topic_map,
        topic=topic,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/locations/add/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    return render_template(
        "location/add.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        map_notes_count=map_notes_count,
    )


@bp.route("/locations/edit/<map_identifier>/<topic_identifier>/<location_identifier>", methods=("GET", "POST"))
@login_required
def edit(map_identifier, topic_identifier, location_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    return render_template(
        "location/edit.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        location_identifier=location_identifier,
        map_notes_count=map_notes_count,
    )


@bp.route("/locations/delete/<map_identifier>/<topic_identifier>/<location_identifier>", methods=("POST",))
@login_required
def delete(map_identifier, topic_identifier, location_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    return redirect(
        url_for(
            "locations.index",
            map_identifier=topic_map.identifier,
            topic_identifier=topic.identifier,
        )
    )
