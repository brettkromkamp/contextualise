import os
import shutil
import uuid

from flask import (Blueprint, session, request, flash, render_template, url_for)
from flask_security import login_required, current_user
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from contextualise.topic_store import get_topic_store

bp = Blueprint('map', __name__)

RESOURCES_DIRECTORY = 'static/resources/'
EXTENSIONS_WHITELIST = {'png', 'jpg', 'jpeg'}


@bp.route('/maps/')
@login_required
def index():
    topic_store = get_topic_store()

    maps = topic_store.get_topic_maps(current_user.id)

    # Reset breadcrumbs and (current) scope/context
    session['breadcrumbs'] = []
    session['current_scope'] = '*'

    return render_template('map/index.html', maps=maps)


@bp.route('/maps/shared/')
def shared():
    topic_store = get_topic_store()

    maps = topic_store.get_shared_topic_maps()

    # Reset breadcrumbs and (current) scope/context
    session['breadcrumbs'] = []
    session['current_scope'] = '*'

    return render_template('map/shared.html', maps=maps)


@bp.route('/maps/create/', methods=('GET', 'POST'))
@login_required
def create():
    topic_store = get_topic_store()

    form_map_name = ''
    form_map_description = ''
    form_map_shared = False

    error = 0

    if request.method == 'POST':
        form_map_name = request.form['map-name'].strip()
        form_map_description = request.form['map-description'].strip()
        form_map_shared = True if request.form['map-shared'] == '1' else False

        # Validate form inputs
        if not form_map_name:
            error = error | 1
        if 'map-image-file' not in request.files:
            error = error | 2
        else:
            upload_file = request.files['map-image-file']
            if upload_file.filename == '':
                error = error | 4
            elif not allowed_file(upload_file.filename):
                error = error | 8

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            image_file_name = f"{str(uuid.uuid4())}.{get_file_extension(upload_file.filename)}"

            # Create and initialise the topic map
            map_identifier = topic_store.set_topic_map(current_user.id, form_map_name, form_map_description,
                                                       image_file_name, initialised=False, shared=form_map_shared,
                                                       promoted=False)
            if map_identifier:
                topic_store.initialise_topic_map(map_identifier)

                # Create the directory for this topic map
                topic_map_directory = os.path.join(bp.root_path, RESOURCES_DIRECTORY, str(map_identifier))
                if not os.path.isdir(topic_map_directory):
                    os.makedirs(topic_map_directory)

                # Upload the image for the topic map to the map's directory
                file_path = os.path.join(topic_map_directory, image_file_name)
                upload_file.save(file_path)

                flash('Map successfully created.', 'success')
            else:
                flash(
                    'An error occurred while creating the topic map. Get in touch with Support if the problem persists.',
                    'danger')
            return redirect(url_for('map.index'))

    return render_template('map/create.html',
                           error=error,
                           map_name=form_map_name,
                           map_description=form_map_description,
                           map_shared=form_map_shared)


@bp.route('/maps/delete/<map_identifier>', methods=('GET', 'POST'))
@login_required
def delete(map_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    if request.method == 'POST':
        # Remove map from topic store
        topic_store.delete_topic_map(map_identifier)

        # Delete the map's directory
        topic_map_directory = os.path.join(bp.root_path, RESOURCES_DIRECTORY, str(map_identifier))
        if os.path.isdir(topic_map_directory):
            shutil.rmtree(topic_map_directory)

        flash('Map successfully deleted.', 'success')
        return redirect(url_for('map.index'))

    return render_template('map/delete.html',
                           topic_map=topic_map)


@bp.route('/maps/edit/<map_identifier>', methods=('GET', 'POST'))
@login_required
def edit(map_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    form_map_name = topic_map.name
    form_map_description = topic_map.description
    form_map_image_path = topic_map.image_path
    form_map_shared = topic_map.shared

    error = 0

    if request.method == 'POST':
        form_map_name = request.form['map-name'].strip()
        form_map_description = request.form['map-description'].strip()
        form_map_shared = True if request.form['map-shared'] == '1' else False

    return render_template('map/edit.html',
                           error=error,
                           topic_map=topic_map,
                           map_name=form_map_name,
                           map_description=form_map_description,
                           map_shared=form_map_shared)


# ========== HELPER METHODS ==========

def get_file_extension(file_name):
    return file_name.rsplit('.', 1)[1].lower()


def allowed_file(file_name):
    return get_file_extension(file_name) in EXTENSIONS_WHITELIST
