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


@bp.route("/temporals/add/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def add(map_identifier, topic_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    if request.method == "POST":
        pass


@bp.route("/temporals/edit/<map_identifier>/<topic_identifier>/<link_identifier>", methods=("GET", "POST"))
@login_required
def edit(map_identifier, topic_identifier, link_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

    if request.method == "POST":
        pass


@bp.route("/temporals/delete/<map_identifier>/<topic_identifier>/<link_identifier>", methods=("POST",))
@login_required
def delete(map_identifier, topic_identifier, link_identifier):
    store, topic_map, topic = initialize(map_identifier, topic_identifier, current_user)

