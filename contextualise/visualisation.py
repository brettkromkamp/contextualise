import maya
from flask import (Blueprint, render_template)
from topicdb.core.store.retrievaloption import RetrievalOption

from contextualise.topic_store import get_topic_store

bp = Blueprint('visualisation', __name__)


@bp.route('/visualisations/<map_identifier>/network/<topic_identifier>')
def network(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    topic = topic_store.get_topic(map_identifier, topic_identifier,
                                  resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)

    occurrences_stats = topic_store.get_topic_occurrences_statistics(map_identifier, topic_identifier)

    creation_date_attribute = topic.get_attribute_by_name('creation-timestamp')
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else 'Undefined'

    return render_template('visualisation/network.html',
                           topic_map=topic_map,
                           topic=topic,
                           creation_date=creation_date,
                           occurrences_stats=occurrences_stats)
