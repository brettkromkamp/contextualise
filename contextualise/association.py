import maya
from flask import (Blueprint, flash, render_template, request, url_for, redirect)
from flask_security import login_required, current_user
from topicdb.core.models.association import Association
from topicdb.core.store.retrievaloption import RetrievalOption
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint('association', __name__)


@bp.route('/associations/<map_identifier>/<topic_identifier>')
@login_required
def index(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    associations = topic_store.get_topic_associations(map_identifier, topic_identifier)

    occurrences_stats = topic_store.get_topic_occurrences_statistics(map_identifier, topic_identifier)

    creation_date_attribute = topic.get_attribute_by_name('creation-timestamp')
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else 'Undefined'

    return render_template('association/index.html',
                           topic_map=topic_map,
                           topic=topic,
                           associations=associations,
                           creation_date=creation_date,
                           occurrences_stats=occurrences_stats)


@bp.route('/associations/<map_identifier>/create/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def create(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    form_association_instance_of = 'association'
    form_association_src_topic_ref = topic_identifier  # The current topic is the 'source' topic
    form_association_src_role_spec = 'related'
    form_association_dest_topic_ref = ''
    form_association_dest_role_spec = 'related'
    form_association_scope = '*'  # Universal scope
    form_association_name = ''
    form_association_identifier = ''

    error = 0

    if request.method == 'POST':
        form_association_dest_topic_ref = request.form['association-dest-topic-ref'].strip()
        form_association_dest_role_spec = request.form['association-dest-role-spec'].strip()
        form_association_src_topic_ref = topic_identifier
        form_association_src_role_spec = request.form['association-src-role-spec'].strip()
        form_association_instance_of = request.form['association-instance-of'].strip()
        form_association_scope = request.form['association-scope'].strip()
        form_association_name = request.form['association-name'].strip()
        form_association_identifier = request.form['association-identifier'].strip()

        # If no values have been provided set their default values
        if not form_association_dest_role_spec:
            form_association_dest_role_spec = 'related'
        if not form_association_src_role_spec:
            form_association_src_role_spec = 'related'
        if not form_association_instance_of:
            form_association_instance_of = 'association'
        if not form_association_scope:
            form_association_scope = '*'  # Universal scope
        if not form_association_name:
            form_association_name = 'Undefined'

        # Validate form inputs
        if not topic_store.topic_exists(topic_map.identifier, form_association_dest_topic_ref):
            error = error | 1
        if form_association_dest_role_spec != 'related' and \
                not topic_store.topic_exists(topic_map.identifier, form_association_dest_role_spec):
            error = error | 2
        if form_association_src_role_spec != 'related' and \
                not topic_store.topic_exists(topic_map.identifier, form_association_src_role_spec):
            error = error | 4
        if form_association_instance_of != 'association' and \
                not topic_store.topic_exists(topic_map.identifier, form_association_instance_of):
            error = error | 8
        if form_association_scope != '*' and not topic_store.topic_exists(topic_map.identifier, form_association_scope):
            error = error | 16
        if form_association_identifier and topic_store.topic_exists(topic_map.identifier, form_association_identifier):
            error = error | 32

        # If role identifier topics are missing then create them
        if error & 2:  # Destination role spec
            pass
        if error & 4:  # Source role spec
            pass

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            association = Association(identifier=form_association_identifier,
                                      instance_of=form_association_instance_of,
                                      base_name=form_association_name,
                                      scope=form_association_scope,
                                      src_topic_ref=form_association_src_topic_ref,
                                      dest_topic_ref=form_association_dest_topic_ref,
                                      src_role_spec=form_association_src_role_spec,
                                      dest_role_spec=form_association_dest_role_spec)

            # Persist association object to the topic store
            topic_store.set_association(map_identifier, association)

            flash('Association successfully created.', 'success')
            return redirect(
                url_for('association.index', map_identifier=topic_map.identifier, topic_identifier=topic_identifier))

    return render_template('association/create.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           association_instance_of=form_association_instance_of,
                           association_src_topic_ref=form_association_src_topic_ref,
                           association_src_role_spec=form_association_src_role_spec,
                           association_dest_topic_ref=form_association_dest_topic_ref,
                           association_dest_role_spec=form_association_dest_role_spec,
                           association_scope=form_association_scope,
                           association_name=form_association_name,
                           association_identifier=form_association_identifier)


@bp.route('/associations/<map_identifier>/delete/<topic_identifier>/<association_identifier>',
          methods=('GET', 'POST'))
@login_required
def delete(map_identifier, topic_identifier, association_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    association = topic_store.get_association(map_identifier, association_identifier)

    if request.method == 'POST':
        topic_store.delete_association(map_identifier, association_identifier)
        flash('Association successfully deleted.', 'warning')
        return redirect(
            url_for('association.index', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('association/delete.html',
                           topic_map=topic_map,
                           topic=topic,
                           association=association)
