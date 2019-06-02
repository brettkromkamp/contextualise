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

bp = Blueprint('file', __name__)

RESOURCES_DIRECTORY = 'static/resources/'


@bp.route('/files/<map_identifier>/<topic_identifier>')
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

    return render_template('file/index.html',
                           topic_map=topic_map,
                           topic=topic,
                           files=files,
                           creation_date=creation_date)


@bp.route('/files/<map_identifier>/upload/<topic_identifier>', methods=('GET', 'POST'))
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

    form_file_title = ''
    form_file_scope = '*'

    error = 0

    if request.method == 'POST':
        form_file_title = request.form['file-title'].strip()
        form_file_scope = request.form['file-scope'].strip()

        # If no values have been provided set their default values
        if not form_file_scope:
            form_file_scope = '*'  # Universal scope

        # Validate form inputs
        if not form_file_title:
            error = error | 1
        if 'file-file' not in request.files:
            error = error | 2
        else:
            upload_file = request.files['file-file']
            if upload_file.filename == '':
                error = error | 4
        if not topic_store.topic_exists(topic_map.identifier, form_file_scope):
            error = error | 8

        if error != 0:
            flash(
                'An error occurred when uploading the file. Please review the warnings and fix accordingly.',
                'warning')
        else:
            file_extension = get_file_extension(upload_file.filename)
            file_file_name = f"{str(uuid.uuid4())}.{file_extension}"
            form_file_title = f"{form_file_title} (.{file_extension})"

            # Create the file directory for this topic map and topic if it doesn't already exist
            file_directory = os.path.join(bp.root_path, RESOURCES_DIRECTORY, str(map_identifier), topic_identifier)
            if not os.path.isdir(file_directory):
                os.makedirs(file_directory)

            file_path = os.path.join(file_directory, file_file_name)
            upload_file.save(file_path)

            file_occurrence = Occurrence(instance_of='file', topic_identifier=topic.identifier,
                                         scope=form_file_scope,
                                         resource_ref=file_file_name)
            title_attribute = Attribute('title', form_file_title, file_occurrence.identifier,
                                        data_type=DataType.STRING)

            # Persist objects to the topic store
            topic_store.set_occurrence(topic_map.identifier, file_occurrence)
            topic_store.set_attribute(topic_map.identifier, title_attribute)

            flash('File successfully uploaded.', 'success')
            return redirect(
                url_for('file.index', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('file/upload.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           file_title=form_file_title,
                           file_scope=form_file_scope)


# ========== HELPER METHODS ==========

def get_file_extension(file_name):
    return file_name.rsplit('.', 1)[1].lower()
