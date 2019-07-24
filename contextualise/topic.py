import os
import shutil
from collections import deque
from datetime import datetime

import maya
import mistune
from flask import (Blueprint, session, flash, render_template, request, url_for, redirect)
from flask_security import login_required, current_user
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.basename import BaseName
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.models.topic import Topic
from topicdb.core.store.retrievaloption import RetrievalOption
from topicdb.core.topicdberror import TopicDbError
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint('topic', __name__)

RESOURCES_DIRECTORY = 'static/resources/'
BREADCRUMBS_COUNT = 3


@bp.route('/topics/view/<map_identifier>/<topic_identifier>')
def view(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)
    else:
        if topic_map.shared:
            if current_user.is_authenticated:  # User is logged in
                if current_user.id != topic_map.user_identifier and topic_identifier == 'home':
                    flash('You are accessing a shared topic map of another user.', 'primary')
        else:
            if current_user.is_authenticated:  # User is logged in
                if current_user.id != topic_map.user_identifier:
                    abort(403)
            else:  # User is *not* logged in
                abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        session['inexistent_topic_identifier'] = topic_identifier
        abort(404)
    else:
        session.pop('inexistent_topic_identifier', None)

    # If a context has been specified in the URL, then use that to set the context
    scope_identifier = request.args.get('context', type=str)
    if scope_identifier and topic_store.topic_exists(map_identifier, scope_identifier):
        session['current_scope'] = scope_identifier

    topic_occurrences = topic_store.get_topic_occurrences(map_identifier, topic_identifier,
                                                          scope=session['current_scope'],
                                                          inline_resource_data=RetrievalOption.INLINE_RESOURCE_DATA,
                                                          resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    occurrences = {
        'text': None,
        'images': [],
        '3d-scenes': [],
        'files': [],
        'links': [],
        'videos': [],
        'notes': []
    }
    for occurrence in topic_occurrences:
        if occurrence.instance_of == 'text':
            if occurrence.resource_data:
                occurrences['text'] = mistune.markdown(occurrence.resource_data.decode())
        elif occurrence.instance_of == 'image':
            occurrences['images'].append({
                'title': occurrence.get_attribute_by_name('title').value,
                'url': occurrence.resource_ref
            })
        elif occurrence.instance_of == '3d-scene':
            occurrences['3d-scenes'].append({
                'title': occurrence.get_attribute_by_name('title').value,
                'url': occurrence.resource_ref
            })
        elif occurrence.instance_of == 'file':
            occurrences['files'].append({
                'title': occurrence.get_attribute_by_name('title').value,
                'url': occurrence.resource_ref
            })
        elif occurrence.instance_of == 'url':
            occurrences['links'].append({
                'title': occurrence.get_attribute_by_name('title').value,
                'url': occurrence.resource_ref
            })
        elif occurrence.instance_of == 'video':
            occurrences['videos'].append({
                'title': occurrence.get_attribute_by_name('title').value,
                'url': occurrence.resource_ref
            })
        elif occurrence.instance_of == 'note':
            occurrences['notes'].append({'identifier': occurrence.identifier,
                                         'title': occurrence.get_attribute_by_name('title').value,
                                         'timestamp': maya.parse(
                                             occurrence.get_attribute_by_name('modification-timestamp').value),
                                         'text': mistune.markdown(occurrence.resource_data.decode())})

    associations = topic_store.get_association_groups(map_identifier, topic_identifier, scope=session['current_scope'])

    creation_date = maya.parse(topic.get_attribute_by_name('creation-timestamp').value)
    modification_date_attribute = topic.get_attribute_by_name('modification-timestamp')
    modification_date = maya.parse(modification_date_attribute.value) if modification_date_attribute else 'Undefined'

    # Breadcrumbs
    if 'breadcrumbs' not in session:
        session['breadcrumbs'] = []
    breadcrumbs = deque(session['breadcrumbs'], BREADCRUMBS_COUNT)
    if topic_identifier in breadcrumbs:
        breadcrumbs.remove(topic_identifier)
    breadcrumbs.append(topic_identifier)
    session['breadcrumbs'] = list(breadcrumbs)

    knowledge_graph_query = topic.get_attribute_by_name('knowledge-graph-query').value if topic.get_attribute_by_name(
        'knowledge-graph-query') else None

    return render_template('topic/view.html',
                           topic_map=topic_map,
                           topic=topic,
                           occurrences=occurrences,
                           associations=associations,
                           creation_date=creation_date,
                           modification_date=modification_date,
                           breadcrumbs=breadcrumbs,
                           knowledge_graph_query=knowledge_graph_query)


@bp.route('/topics/create/<map_identifier>/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def create(map_identifier, topic_identifier):
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

    form_topic_name = ''
    form_topic_identifier = ''
    form_topic_text = ''
    form_topic_instance_of = 'topic'
    form_topic_text_scope = session['current_scope']

    error = 0

    if request.method == 'POST':
        form_topic_identifier = request.form['topic-identifier'].strip()
        form_topic_name = request.form['topic-name'].strip()
        form_topic_text = request.form['topic-text'].strip()
        form_topic_instance_of = request.form['topic-instance-of'].strip()
        form_topic_text_scope = request.form['topic-text-scope'].strip()

        # If no values have been provided set their default values
        if not form_topic_instance_of:
            form_topic_instance_of = 'topic'

        # Validate form inputs
        if not form_topic_name:
            error = error | 1
        if topic_store.topic_exists(topic_map.identifier, form_topic_identifier):
            error = error | 2
        if not form_topic_identifier:
            error = error | 4
        if not topic_store.topic_exists(topic_map.identifier, form_topic_instance_of):
            error = error | 8
        if not topic_store.topic_exists(topic_map.identifier, form_topic_text_scope):
            error = error | 16

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            new_topic = Topic(form_topic_identifier, form_topic_instance_of, form_topic_name)
            text_occurrence = Occurrence(instance_of='text', topic_identifier=new_topic.identifier,
                                         scope=form_topic_text_scope,
                                         resource_data=form_topic_text)
            timestamp = str(datetime.now())
            modification_attribute = Attribute('modification-timestamp', timestamp, new_topic.identifier,
                                               data_type=DataType.TIMESTAMP)

            query_attribute = Attribute('knowledge-graph-query', form_topic_name.lower(), new_topic.identifier,
                                        data_type=DataType.STRING)

            # Persist objects to the topic store
            topic_store.set_topic(topic_map.identifier, new_topic)
            topic_store.set_occurrence(topic_map.identifier, text_occurrence)
            topic_store.set_attribute(topic_map.identifier, modification_attribute)
            topic_store.set_attribute(topic_map.identifier, query_attribute)

            flash('Topic successfully created.', 'success')
            return redirect(
                url_for('topic.view', map_identifier=topic_map.identifier, topic_identifier=new_topic.identifier))

    return render_template('topic/create.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           topic_name=form_topic_name,
                           topic_identifier=form_topic_identifier,
                           topic_text=form_topic_text,
                           topic_instance_of=form_topic_instance_of,
                           topic_text_scope=form_topic_text_scope)


@bp.route('/topics/edit/<map_identifier>/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def edit(map_identifier, topic_identifier):
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

    occurrences = topic_store.get_topic_occurrences(map_identifier, topic_identifier,
                                                    scope=session['current_scope'],
                                                    inline_resource_data=RetrievalOption.INLINE_RESOURCE_DATA)

    texts = [occurrence for occurrence in occurrences if occurrence.instance_of == 'text']

    form_topic_name = topic.first_base_name.name
    form_topic_text = texts[0].resource_data.decode() if texts[0].resource_data else ''
    form_topic_instance_of = topic.instance_of
    form_topic_text_scope = texts[0].scope if texts else session['current_scope']  # Should it be '*'?

    error = 0

    if request.method == 'POST':
        form_topic_name = request.form['topic-name'].strip()
        form_topic_text = request.form['topic-text'].strip()
        form_topic_instance_of = request.form['topic-instance-of'].strip()
        form_topic_text_scope = request.form['topic-text-scope'].strip()

        # If no values have been provided set their default values
        if not form_topic_instance_of:
            form_topic_instance_of = 'topic'

        # Validate form inputs
        if not topic_store.topic_exists(topic_map.identifier, form_topic_instance_of):
            error = error | 1
        if not topic_store.topic_exists(topic_map.identifier, form_topic_text_scope):
            error = error | 2

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            # Update topic's first base name if it has changed
            if topic.first_base_name.name != form_topic_name:
                topic_store.update_basename(map_identifier, topic.first_base_name.identifier, form_topic_name)

            # Update topic's 'instance of' if it has changed
            if topic.instance_of != form_topic_instance_of:
                topic_store.update_topic_instance_of(map_identifier, topic.identifier, form_topic_instance_of)

            # If the topic has an existing text occurrence update it, otherwise create a new text occurrence
            # and persist it
            if texts:
                topic_store.update_occurrence_data(map_identifier, texts[0].identifier, form_topic_text)
            else:
                text_occurrence = Occurrence(instance_of='text', topic_identifier=topic.identifier,
                                             scope=form_topic_text_scope,
                                             resource_data=form_topic_text)
                topic_store.set_occurrence(topic_map.identifier, text_occurrence)

            # Update the topic's modification (timestamp) attribute
            timestamp = str(datetime.now())
            if topic.get_attribute_by_name('modification-timestamp'):
                topic_store.update_attribute_value(topic_map.identifier,
                                                   topic.get_attribute_by_name('modification-timestamp').identifier,
                                                   timestamp)
            else:
                modification_attribute = Attribute('modification-timestamp', timestamp, topic.identifier,
                                                   data_type=DataType.TIMESTAMP)
                topic_store.set_attribute(topic_map.identifier, modification_attribute)

            flash('Topic successfully updated.', 'success')
            return redirect(
                url_for('topic.view', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('topic/edit.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           topic_name=form_topic_name,
                           topic_identifier=topic.identifier,
                           topic_text=form_topic_text,
                           topic_instance_of=form_topic_instance_of,
                           topic_text_scope=form_topic_text_scope)


@bp.route('/topics/delete/<map_identifier>/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def delete(map_identifier, topic_identifier):
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

    if request.method == 'POST':
        try:
            # Remove the topic from the topic store
            topic_store.delete_topic(map_identifier, topic_identifier)

            # Remove the topic's resources directory
            topic_directory = os.path.join(bp.root_path, RESOURCES_DIRECTORY, str(map_identifier), topic_identifier)
            if os.path.isdir(topic_directory):
                shutil.rmtree(topic_directory)
        except TopicDbError:
            flash(
                'Topic not deleted. Certain predefined topics are required for Contextualise to function correctly. Perhaps, you attempted to delete one of those topics.',
                'warning')
            return redirect(
                url_for('topic.view', map_identifier=topic_map.identifier, topic_identifier=topic_identifier))

        flash('Topic successfully deleted.', 'success')
        return redirect(url_for('map.index'))

    return render_template('topic/delete.html',
                           topic_map=topic_map,
                           topic=topic)


@bp.route('/topics/add-note/<map_identifier>/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def add_note(map_identifier, topic_identifier):
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

    form_note_title = ''
    form_note_text = ''
    form_note_scope = '*'

    error = 0

    if request.method == 'POST':
        form_note_title = request.form['note-title'].strip()
        form_note_text = request.form['note-text'].strip()
        form_note_scope = request.form['note-scope'].strip()

        # If no values have been provided set their default values
        if not form_note_scope:
            form_note_scope = '*'  # Universal scope

        # Validate form inputs
        if not form_note_title:
            error = error | 1
        if not form_note_text:
            error = error | 2
        if not topic_store.topic_exists(topic_map.identifier, form_note_scope):
            error = error | 4

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            note_occurrence = Occurrence(instance_of='note', topic_identifier=topic.identifier,
                                         scope=form_note_scope,
                                         resource_data=form_note_text)
            title_attribute = Attribute('title', form_note_title, note_occurrence.identifier,
                                        data_type=DataType.STRING)
            timestamp = str(datetime.now())
            modification_attribute = Attribute('modification-timestamp', timestamp, note_occurrence.identifier,
                                               data_type=DataType.TIMESTAMP)

            # Persist objects to the topic store
            topic_store.set_occurrence(topic_map.identifier, note_occurrence)
            topic_store.set_attribute(topic_map.identifier, title_attribute)
            topic_store.set_attribute(topic_map.identifier, modification_attribute)

            flash('Note successfully added.', 'success')
            return redirect(
                url_for('topic.view', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('topic/add_note.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           note_title=form_note_title,
                           note_text=form_note_text,
                           note_scope=form_note_scope)


@bp.route('/topics/edit-note/<map_identifier>/<topic_identifier>/<note_identifier>', methods=('GET', 'POST'))
@login_required
def edit_note(map_identifier, topic_identifier, note_identifier):
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

    note_occurrence = topic_store.get_occurrence(map_identifier, note_identifier,
                                                 inline_resource_data=RetrievalOption.INLINE_RESOURCE_DATA,
                                                 resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)

    form_note_title = note_occurrence.get_attribute_by_name('title').value
    form_note_text = note_occurrence.resource_data.decode()
    form_note_scope = note_occurrence.scope

    error = 0

    if request.method == 'POST':
        form_note_title = request.form['note-title'].strip()
        form_note_text = request.form['note-text'].strip()
        form_note_scope = request.form['note-scope'].strip()

        # If no values have been provided set their default values
        if not form_note_scope:
            form_note_scope = '*'  # Universal scope

        # Validate form inputs
        if not form_note_title:
            error = error | 1
        if not form_note_text:
            error = error | 2
        if not topic_store.topic_exists(topic_map.identifier, form_note_scope):
            error = error | 4

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            # Update note's title if it has changed
            if note_occurrence.get_attribute_by_name('title').value != form_note_title:
                topic_store.update_attribute_value(topic_map.identifier,
                                                   note_occurrence.get_attribute_by_name('title').identifier,
                                                   form_note_title)

            # Update the note's modification (timestamp) attribute
            timestamp = str(datetime.now())
            topic_store.update_attribute_value(topic_map.identifier,
                                               note_occurrence.get_attribute_by_name(
                                                   'modification-timestamp').identifier,
                                               timestamp)

            # Update note (occurrence)
            topic_store.update_occurrence_data(map_identifier, note_occurrence.identifier, form_note_text)

            # Update note's scope if it has changed
            if note_occurrence.scope != form_note_scope:
                topic_store.update_occurrence_scope(map_identifier, note_occurrence.identifier, form_note_scope)

            flash('Note successfully updated.', 'success')
            return redirect(
                url_for('topic.view', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('topic/edit_note.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           note_identifier=note_occurrence.identifier,
                           note_title=form_note_title,
                           note_text=form_note_text,
                           note_scope=form_note_scope)


@bp.route('/topics/delete-note/<map_identifier>/<topic_identifier>/<note_identifier>', methods=('GET', 'POST'))
@login_required
def delete_note(map_identifier, topic_identifier, note_identifier):
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

    note_occurrence = topic_store.get_occurrence(map_identifier, note_identifier,
                                                 inline_resource_data=RetrievalOption.INLINE_RESOURCE_DATA,
                                                 resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)

    form_note_title = note_occurrence.get_attribute_by_name('title').value
    form_note_text = mistune.markdown(note_occurrence.resource_data.decode())
    form_note_scope = note_occurrence.scope

    if request.method == 'POST':
        topic_store.delete_occurrence(map_identifier, note_occurrence.identifier)
        flash('Note successfully deleted.', 'warning')
        return redirect(
            url_for('topic.view', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('topic/delete_note.html',
                           topic_map=topic_map,
                           topic=topic,
                           note_identifier=note_occurrence.identifier,
                           note_title=form_note_title,
                           note_text=form_note_text,
                           note_scope=form_note_scope)


@bp.route('/topics/view-names/<map_identifier>/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def view_names(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)
    if 'admin' not in current_user.roles:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)

    if topic is None:
        abort(404)

    creation_date_attribute = topic.get_attribute_by_name('creation-timestamp')
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else 'Undefined'

    return render_template('topic/view_names.html',
                           topic_map=topic_map,
                           topic=topic,
                           creation_date=creation_date)


@bp.route('/topics/add-name/<map_identifier>/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def add_name(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)
    if 'admin' not in current_user.roles:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    form_topic_name = ''

    error = 0

    if request.method == 'POST':
        form_topic_name = request.form['topic-name'].strip()

        # Validate form inputs
        if not form_topic_name:
            error = error | 1

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            base_name = BaseName(form_topic_name)
            topic_store.set_basename(map_identifier, topic.identifier, base_name)

            flash('Name successfully added.', 'success')
            return redirect(
                url_for('topic.view_names', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('topic/add_name.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           topic_name=form_topic_name)


@bp.route('/topics/edit-name/<map_identifier>/<topic_identifier>/<name_identifier>', methods=('GET', 'POST'))
@login_required
def edit_name(map_identifier, topic_identifier, name_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)
    if 'admin' not in current_user.roles:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    form_topic_name = topic.get_base_name(name_identifier).name

    error = 0

    if request.method == 'POST':
        form_topic_name = request.form['topic-name'].strip()

        # Validate form inputs
        if not form_topic_name:
            error = error | 1

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            # Update name if required
            if form_topic_name != topic.get_base_name(name_identifier).name:
                topic_store.update_basename(map_identifier, name_identifier, form_topic_name)

            flash('Name successfully updated.', 'success')
            return redirect(
                url_for('topic.view_names', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('topic/edit_name.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           topic_name=form_topic_name,
                           name_identifier=name_identifier)


@bp.route('/topics/delete-name/<map_identifier>/<topic_identifier>/<name_identifier>', methods=('GET', 'POST'))
@login_required
def delete_name(map_identifier, topic_identifier, name_identifier):
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

    form_topic_name = topic.get_base_name(name_identifier).name

    if request.method == 'POST':
        topic_store.delete_basename(map_identifier, name_identifier)

        flash('Name successfully deleted.', 'warning')
        return redirect(
            url_for('topic.view_names', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('topic/delete_name.html',
                           topic_map=topic_map,
                           topic=topic,
                           topic_name=form_topic_name,
                           name_identifier=name_identifier)


@bp.route('/topics/change-context/<map_identifier>/<topic_identifier>/<scope_identifier>', methods=('GET', 'POST'))
@login_required
def change_context(map_identifier, topic_identifier, scope_identifier):
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

    form_scope = scope_identifier

    error = 0

    if request.method == 'POST':
        form_scope = request.form['new-scope'].strip()

        # If no values have been provided set their default values
        if not form_scope:
            form_scope = '*'  # Universal scope/context

        # Validate form inputs
        if not topic_store.topic_exists(topic_map.identifier, form_scope):
            error = error | 1

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            session['current_scope'] = form_scope
            flash('Context successfully changed.', 'success')
            return redirect(
                url_for('topic.view', map_identifier=topic_map.identifier, topic_identifier=topic.identifier))

    return render_template('topic/change_context.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           scope_identifier=form_scope)
