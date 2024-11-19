"""
location.py file. Part of the Contextualise project.

November 19, 2024
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import re

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

bp = Blueprint("location", __name__)


# region Functions
def _validate_coordinates(coordinates_string: str) -> bool:
    """
    Validate a string with (latitude/longitude) coordinates using regex.
    :param coordinates_string: The input date string in 'latitude, longitude' format.
    :return: True if valid, False otherwise.
    """
    # Regex pattern
    coordinates_regex = r"^\s*([-+]?(?:90(?:\.0+)?|(?:[1-8]?\d(?:\.\d+)?)))\s*,\s*([-+]?(?:180(?:\.0+)?|(?:1[0-7]\d(?:\.\d+)?|(?:[1-9]?\d(?:\.\d+)?))))\s*$"

    # Step 1: Check the format using regex
    if not re.match(coordinates_regex, coordinates_string):
        return False

    return True


# endregion


@bp.route("/locations/<map_identifier>/<topic_identifier>")
@login_required
def index(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    location_occurrences = store.get_topic_occurrences(
        map_identifier,
        topic_identifier,
        "location",
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    locations = []
    for location_occurrence in location_occurrences:
        locations.append(
            {
                "identifier": location_occurrence.identifier,
                "topic_identifier": location_occurrence.topic_identifier,
                "name": location_occurrence.get_attribute_by_name("location-name").value,
                "description": location_occurrence.resource_data.decode("utf-8")
                if location_occurrence.has_data
                else None,
                "coordinates": location_occurrence.get_attribute_by_name("geographic-coordinates").value,
                "scope": location_occurrence.scope,
            }
        )

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]

    return render_template(
        "location/index.html",
        topic_map=topic_map,
        topic=topic,
        locations=locations,
        creation_date=creation_date,
        map_notes_count=map_notes_count,
    )


@bp.route("/locations/add/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    map_notes_count = store.get_topic_occurrences_statistics(map_identifier, "notes")["note"]
    error = 0

    locations = store.get_topic_occurrences(
        map_identifier=map_identifier,
        identifier=topic_identifier,
        instance_of="location",
        inline_resource_data=RetrievalMode.INLINE_RESOURCE_DATA,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    location = locations[0] if locations else None

    if request.method == "POST":
        form_location_name = request.form.get("location-name")
        form_location_description = request.form.get("location-description")
        form_location_coordinates = request.form.get("location-coordinates")
        form_location_scope = request.form.get("location-scope")

        # If no values have been provided set their default values
        if not form_location_scope:
            form_location_scope = session["current_scope"]

        # Validate form inputs
        if not form_location_name:
            error = error | 1
        if not form_location_description:
            error = error | 2
        if not form_location_coordinates:
            error = error | 4

        if error != 0:
            flash(
                "An error occurred when submitting the form. Review the warnings and fix accordingly.",
                "warning",
            )
        else:
            location_occurrence = Occurrence(
                instance_of="location",
                topic_identifier=topic_identifier,
                scope=form_location_scope,
                resource_data=form_location_description,
            )
            name_attribute = Attribute(
                "location-name",
                form_location_name,
                location_occurrence.identifier,
                data_type=DataType.STRING,
            )
            coordinates_attribute = Attribute(
                "geographic-coordinates",
                form_location_coordinates,
                location_occurrence.identifier,
                data_type=DataType.STRING,
            )
            store.create_occurrence(topic_map.identifier, location_occurrence, ontology_mode=OntologyMode.LENIENT)
            store.create_attribute(topic_map.identifier, name_attribute, ontology_mode=OntologyMode.LENIENT)
            store.create_attribute(topic_map.identifier, coordinates_attribute, ontology_mode=OntologyMode.LENIENT)

            flash("Location successfully added.", "success")
            return redirect(
                url_for(
                    "location.index",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                )
            )
        return render_template(
            "location/add.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            location=location,
            location_topic_identifier=topic_identifier,
            location_description=form_location_description,
            location_coordinates=form_location_coordinates,
            location_scope=form_location_scope,
            map_notes_count=map_notes_count,
        )

    if location:
        location_description = location.resource_data.decode("utf-8") if location.has_data else None
        location_coordinates = location.get_attribute_by_name("geographic-coordinates").value
        location_scope = location.scope
        flash("This topic has already been defined as a location.", "warning")
    return render_template(
        "location/add.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        location=location,
        location_topic_identifier=location.topic_identifier if location else None,
        location_description=location_description if location else None,
        location_coordinates=location_coordinates if location else None,
        location_scope=location_scope if location else None,
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

    error = 0

    location_occurrence = store.get_occurrence(
        map_identifier,
        location_identifier,
        resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )

    if not location_occurrence:
        error = error | 1

    if error != 0:
        flash("An error occurred while trying to delete the location.", "warning")
    else:
        try:
            # Delete location occurrence from topic store
            store.delete_occurrence(map_identifier, location_occurrence.identifier)
            flash("Location successfully deleted.", "success")
        except TopicDbError:
            flash(
                "An error occurred while trying to delete the location. The location was not deleted.",
                "warning",
            )

    return redirect(
        url_for(
            "location.index",
            map_identifier=topic_map.identifier,
            topic_identifier=topic.identifier,
        )
    )
