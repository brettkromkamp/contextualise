from datetime import datetime

import maya
import mistune
from flask import (Blueprint, flash, render_template, request, url_for, redirect)
from flask_security import login_required, current_user
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.models.topic import Topic
from topicdb.core.store.retrievaloption import RetrievalOption
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint('note', __name__)


@bp.route('/notes/index/<map_identifier>')
def index(map_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)
    else:
        if not topic_map.shared:
            if current_user.is_authenticated:  # User is logged in
                if current_user.id != topic_map.user_identifier:
                    abort(403)
            else:  # User is *not* logged in
                abort(403)

    topic = topic_store.get_topic(map_identifier, 'home')

    note_occurrences = topic_store.get_topic_occurrences(map_identifier, 'notes', 'note',
                                                         inline_resource_data=RetrievalOption.INLINE_RESOURCE_DATA,
                                                         resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    notes = []
    for note_occurrence in note_occurrences:
        notes.append({'identifier': note_occurrence.identifier,
                      'title': note_occurrence.get_attribute_by_name('title').value,
                      'timestamp': maya.parse(note_occurrence.get_attribute_by_name('modification-timestamp').value),
                      'text': mistune.markdown(note_occurrence.resource_data.decode())})

    return render_template('note/index.html',
                           topic_map=topic_map,
                           topic=topic,
                           notes=notes)


@bp.route('/notes/add/<map_identifier>', methods=('GET', 'POST'))
@login_required
def add(map_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, 'home',
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
            note_occurrence = Occurrence(instance_of='note', topic_identifier='notes',
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
                url_for('note.index', map_identifier=topic_map.identifier))

    return render_template('note/add.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           note_title=form_note_title,
                           note_text=form_note_text,
                           note_scope=form_note_scope)


@bp.route('/notes/attach/<map_identifier>/<note_identifier>', methods=('GET', 'POST'))
@login_required
def attach(map_identifier, note_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, 'home',
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if topic is None:
        abort(404)

    note_occurrence = topic_store.get_occurrence(map_identifier, note_identifier,
                                                 inline_resource_data=RetrievalOption.INLINE_RESOURCE_DATA,
                                                 resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)

    form_note_title = note_occurrence.get_attribute_by_name('title').value
    form_note_text = mistune.markdown(note_occurrence.resource_data.decode())
    form_note_scope = note_occurrence.scope

    error = 0

    if request.method == 'POST':
        form_note_topic_identifier = request.form['note-topic-identifier'].strip()

        # Validate form inputs
        if not topic_store.topic_exists(topic_map.identifier, form_note_topic_identifier):
            error = error | 1

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            topic_store.update_occurrence_topic_identifier(map_identifier, note_identifier, form_note_topic_identifier)
            flash('Note successfully attached.', 'success')
            return redirect(
                url_for('topic.view', map_identifier=topic_map.identifier, topic_identifier=form_note_topic_identifier))

    return render_template('note/attach.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           note_identifier=note_occurrence.identifier,
                           note_title=form_note_title,
                           note_text=form_note_text,
                           note_scope=form_note_scope)


@bp.route('/notes/convert/<map_identifier>/<note_identifier>', methods=('GET', 'POST'))
@login_required
def convert(map_identifier, note_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if topic_map is None:
        abort(404)

    if current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, 'home',
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)

    if topic is None:
        abort(404)

    note_occurrence = topic_store.get_occurrence(map_identifier, note_identifier,
                                                 inline_resource_data=RetrievalOption.INLINE_RESOURCE_DATA,
                                                 resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    note_title = note_occurrence.get_attribute_by_name('title').value

    form_topic_name = ''
    form_topic_identifier = ''
    form_topic_text = "## " + note_title + "\n" + note_occurrence.resource_data.decode()

    form_topic_instance_of = 'topic'

    error = 0

    if request.method == 'POST':
        form_topic_identifier = request.form['topic-identifier'].strip()
        form_topic_name = request.form['topic-name'].strip()
        form_topic_text = request.form['topic-text']
        form_topic_instance_of = request.form['topic-instance-of'].strip()

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

        if error != 0:
            flash(
                'An error occurred when submitting the form. Please review the warnings and fix accordingly.',
                'warning')
        else:
            new_topic = Topic(form_topic_identifier, form_topic_instance_of, form_topic_name)
            text_occurrence = Occurrence(instance_of='text', topic_identifier=new_topic.identifier,
                                         resource_data=form_topic_text)
            timestamp = str(datetime.now())
            modification_attribute = Attribute('modification-timestamp', timestamp, new_topic.identifier,
                                               data_type=DataType.TIMESTAMP)

            # Persist objects to the topic store
            topic_store.set_topic(topic_map.identifier, new_topic)
            topic_store.set_occurrence(topic_map.identifier, text_occurrence)
            topic_store.set_attribute(topic_map.identifier, modification_attribute)

            # Remove the original note occurrence
            topic_store.delete_occurrence(topic_map.identifier, note_identifier)

            flash('Note successfully converted.', 'success')
            return redirect(
                url_for('topic.view', map_identifier=topic_map.identifier, topic_identifier=new_topic.identifier))

    return render_template('note/convert.html',
                           error=error,
                           topic_map=topic_map,
                           topic=topic,
                           topic_name=form_topic_name,
                           topic_identifier=form_topic_identifier,
                           topic_text=form_topic_text,
                           topic_instance_of=form_topic_instance_of,
                           note_identifier=note_identifier)
