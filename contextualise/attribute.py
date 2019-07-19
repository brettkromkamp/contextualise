from flask import (Blueprint, render_template, request)
from flask_login import current_user
from flask_security import login_required
from topicdb.core.store.retrievaloption import RetrievalOption
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint('attribute', __name__)


@bp.route('/attributes/<map_identifier>/<topic_identifier>')
@login_required
def index_topic(map_identifier, topic_identifier):
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

    attributes = []
    entity_attributes = topic_store.get_attributes(map_identifier, topic_identifier)

    for entity_attribute in entity_attributes:
        attributes.append({'identifier': entity_attribute.identifier,
                           'name': entity_attribute.name,
                           'value': entity_attribute.value,
                           'type': str(entity_attribute.data_type).lower(),
                           'scope': entity_attribute.scope,
                           'language': str(entity_attribute.language).lower()})

    entity_type = 'topic'
    return_url = 'topic.view'

    return render_template('attribute/index.html',
                           topic_map=topic_map,
                           topic=topic,
                           entity_type=entity_type,
                           return_url=return_url,
                           attributes=attributes)


@bp.route('/attributes/<map_identifier>/<topic_identifier>/<entity_identifier>')
@login_required
def index_entity(map_identifier, topic_identifier, entity_identifier):
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

    entity = topic_store.get_association(map_identifier, entity_identifier,
                                         resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if entity is None:
        entity = topic_store.get_occurrence(map_identifier, entity_identifier)

    if entity is None:
        abort(404)

    entity_type = request.args.get('type').lower()
    return_url = None
    if entity_type == 'association':
        return_url = 'association.index'
    elif entity_type == 'image':
        return_url = 'image.index'
    elif entity_type == '3d-scene':
        return_url = 'three_d.index'
    elif entity_type == 'file':
        return_url = 'file.index'
    elif entity_type == 'link':
        return_url = 'link.index'
    elif entity_type == 'video':
        return_url = 'video.index'

    attributes = []
    entity_attributes = topic_store.get_attributes(map_identifier, entity_identifier)

    for entity_attribute in entity_attributes:
        attributes.append({'identifier': entity_attribute.identifier,
                           'name': entity_attribute.name,
                           'value': entity_attribute.value,
                           'type': str(entity_attribute.data_type).lower(),
                           'scope': entity_attribute.scope,
                           'language': str(entity_attribute.language).lower()})

    return render_template('attribute/index.html',
                           topic_map=topic_map,
                           topic=topic,
                           entity=entity,
                           entity_type=entity_type,
                           return_url=return_url,
                           attributes=attributes)


@bp.route('/attributes/add/<map_identifier>/<topic_identifier>', methods=('GET', 'POST'))
@login_required
def add_topic(map_identifier, topic_identifier):
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


@bp.route('/attributes/add/<map_identifier>/<topic_identifier>/<entity_identifier>', methods=('GET', 'POST'))
@login_required
def add_entity(map_identifier, topic_identifier, entity_identifier):
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

    entity = topic_store.get_association(map_identifier, entity_identifier,
                                         resolve_attributes=RetrievalOption.RESOLVE_ATTRIBUTES)
    if entity is None:
        entity = topic_store.get_occurrence(map_identifier, entity_identifier)

    if entity is None:
        abort(404)

    entity_type = request.args.get('type').lower()