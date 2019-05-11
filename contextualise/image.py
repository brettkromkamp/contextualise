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

bp = Blueprint('image', __name__)

IMAGES_UPLOAD_FOLDER = 'static/resources/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


@bp.route('/images/<map_identifier>/<topic_identifier>')
def index(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    image_occurrences = topic_store.get_topic_occurrences(map_identifier, topic_identifier, 'image',
                                                          resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)

    images = []
    for image_occurrence in image_occurrences:
        images.append({'identifier': image_occurrence.identifier,
                       'title': image_occurrence.get_attribute_by_name('title').value,
                       'scope': image_occurrence.scope,
                       'url': image_occurrence.resource_ref})

    occurrences_stats = topic_store.get_topic_occurrences_statistics(map_identifier, topic_identifier)

    creation_date_attribute = topic.get_attribute_by_name('creation-timestamp')
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else 'Undefined'

    return render_template('image/index.html',
                           topic_map=topic_map,
                           topic=topic,
                           images=images,
                           creation_date=creation_date,
                           occurrences_stats=occurrences_stats)


@bp.route('/images/<map_identifier>/upload/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def upload(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    form_image_title = ''
    form_image_scope = '*'

    error = 0

    if request.method == 'POST':
        form_image_title = request.form['image-title'].strip()
        form_image_scope = request.form['image-scope'].strip()

        # If no values have been provided set their default values
        if not form_image_scope:
            form_image_scope = '*'  # Universal scope

        # Validate form inputs
        if not form_image_title:
            error = error | 1
        if 'image-file' not in request.files:
            error = error | 2
        else:
            upload_file = request.files['image-file']
            if upload_file.filename == '':
                error = error | 4
            elif not allowed_file(upload_file.filename):
                error = error | 8
        if not topic_store.topic_exists(topic_map.identifier, form_image_scope):
            error = error | 16

        if error != 0:
            flash(
                'An error occurred when uploading the image. Please review the warnings and fix accordingly.',
                'warning')
        else:
            image_file_name = f"{str(uuid.uuid4())}.{get_file_extension(upload_file.filename)}"
            file_path = os.path.join(bp.root_path, IMAGES_UPLOAD_FOLDER, image_file_name)
            upload_file.save(file_path)

            image_occurrence = Occurrence(instance_of='image', topic_identifier=topic.identifier,
                                          scope=form_image_scope,
                                          resource_ref=image_file_name)
            title_attribute = Attribute('title', form_image_title, image_occurrence.identifier,
                                        data_type=DataType.STRING)

            # Persist objects to the topic store
            topic_store.set_occurrence(topic_map.identifier, image_occurrence)
            topic_store.set_attribute(topic_map.identifier, title_attribute)

            flash('Image successfully uploaded.', 'success')
            return redirect(
                url_for('image.index', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('image/upload.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           image_title=form_image_title,
                           image_scope=form_image_scope)


# ========== HELPER METHODS ==========

def get_file_extension(file_name):
    return file_name.rsplit('.', 1)[1].lower()


def allowed_file(file_name):
    return get_file_extension(file_name) in ALLOWED_EXTENSIONS
