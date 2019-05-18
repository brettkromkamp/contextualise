from datetime import datetime

import maya
import mistune
from flask import (Blueprint, flash, render_template, request, url_for, redirect)
from flask_security import login_required, current_user
from topicdb.core.models.attribute import Attribute
from topicdb.core.models.datatype import DataType
from topicdb.core.models.occurrence import Occurrence
from topicdb.core.store.retrievaloption import RetrievalOption
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint('note', __name__)


@bp.route('/notes/<map_identifier>/index')
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


@bp.route('/notes/<map_identifier>/add', methods=('GET', 'POST'))
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
        form_note_text = request.form['note-text']
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
