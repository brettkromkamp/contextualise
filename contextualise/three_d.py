import os
import uuid

import maya
from flask import (Blueprint, render_template, request, flash, url_for, redirect)
from flask_login import current_user
from flask_security import login_required
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.store.retrievaloption import RetrievalOption
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint('three_d', __name__)

RESOURCES_DIRECTORY = 'static/resources/'
EXTENSIONS_WHITELIST = {'gltf', 'glb'}


@bp.route('/three-d/<map_identifier>/<topic_identifier>')
@login_required
def index(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    file_occurrences = topic_store.get_topic_occurrences(map_identifier, topic_identifier, 'file',
                                                         resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)

    files = []
    for file_occurrence in file_occurrences:
        files.append({'identifier': file_occurrence.identifier,
                      'title': file_occurrence.get_attribute_by_name('title').value,
                      'scope': file_occurrence.scope,
                      'url': file_occurrence.resource_ref})

    creation_date_attribute = topic.get_attribute_by_name('creation-timestamp')
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else 'Undefined'

    return render_template('three_d/index.html',
                           topic_map=topic_map,
                           topic=topic)


@bp.route('/three-d/upload/<map_identifier>/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def upload(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    # TODO

    error = 0

    if request.method == 'POST':
        # TODO
        if error != 0:
            flash(
                'An error occurred when uploading the 3D content. Please review the warnings and fix accordingly.',
                'warning')
        else:
            # TODO

            flash('3D content successfully uploaded.', 'success')
            return redirect(
                url_for('three_d.index', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('three_d/upload.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic)


@bp.route('/three-d/edit/<map_identifier>/<topic_identifier>/<file_identifier>', methods=('GET', 'POST'))
@login_required
def edit(map_identifier, topic_identifier, file_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    # TODO

    error = 0

    if request.method == 'POST':
        # TODO

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            # Update title if it has changed
            # TODO

            # Update scope if it has changed
            # TODO

            flash('3D content successfully updated.', 'success')
            return redirect(
                url_for('three_d.index', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('three_d/edit.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic)


@bp.route('/three-d/delete/<map_identifier>/<topic_identifier>/<file_identifier>', methods=('GET', 'POST'))
@login_required
def delete(map_identifier, topic_identifier, file_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    # TODO

    if request.method == 'POST':
        # TODO

        flash('3D content successfully deleted.', 'warning')
        return redirect(
            url_for('three_d.index', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('three_d/delete.html',
                           topic_map=topic_map,
                           topic=topic)


# ========== HELPER METHODS ==========

def get_file_extension(file_name):
    return file_name.rsplit('.', 1)[1].lower()


def allowed_file(file_name):
    return get_file_extension(file_name) in EXTENSIONS_WHITELIST
