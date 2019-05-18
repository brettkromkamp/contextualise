from flask import (Blueprint, render_template)
from flask_security import login_required
from topicdb.core.store.retrievaloption import RetrievalOption

from contextualise.topic_store import get_topic_store

bp = Blueprint('note', __name__)


@bp.route('/notes/<map_identifier>/index')
def index(map_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    topic = topic_store.get_topic(map_identifier, 'home')

    notes = topic_store.get_topic_occurrences(map_identifier, 'notes', 'note',
                                              inline_resource_data=RetrievalOption.INLINE_RESOURCE_DATA,
                                              resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)

    return render_template('note/index.html',
                           topic_map=topic_map,
                           topic=topic,
                           notes=notes)


@bp.route('/notes/<map_identifier>/add', methods=('GET', 'POST'))
@login_required
def add(map_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    return render_template('note/add.html',
                           topic_map=topic_map)
