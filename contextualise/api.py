from flask import (Blueprint, request, jsonify)
from flask_security import login_required, current_user
from slugify import slugify
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint('api', __name__)


@bp.route('/api/get-slug')
@login_required
def get_slug():
    value = request.args.get('value', '')

    return jsonify({
        "value": value,
        "slug": slugify(str(value))
    })


@bp.route('/api/<map_identifier>/get-identifiers')
@login_required
def get_identifiers(map_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if not topic_map.shared and current_user.id != topic_map.user_identifier:
        abort(403)

    query_term = request.args.get('q').lower()

    return jsonify(topic_store.get_topic_identifiers(map_identifier, query_term, limit=10))


@bp.route('/api/<map_identifier>/get-network/<topic_identifier>')
@login_required
def get_network(map_identifier, topic_identifier):
    topic_store = get_topic_store()
    topic_map = topic_store.get_topic_map(map_identifier)

    if not topic_map.shared and current_user.id != topic_map.user_identifier:
        abort(403)

    topic = topic_store.get_topic(map_identifier, topic_identifier)

    def build_network(inner_identifier):
        base_name = tree[inner_identifier].topic.first_base_name.name
        instance_of = tree[inner_identifier].topic.instance_of
        children = tree[inner_identifier].children

        group = instance_of
        if inner_identifier == topic_identifier:
            group = 'active'
        node = {
            'id': inner_identifier,
            'label': base_name,
            'group': group,
            'instanceOf': instance_of
        }

        result[nodes].append(node)

        for child in children:
            edge = {
                'from': inner_identifier,
                'to': child,
                'arrows': 'to, from',
                'color': {'color': '#666', 'opacity': 0.5}
            }
            result[edges].append(edge)
            build_network(child)  # Recursive call.

    if topic:
        tree = topic_store.get_topics_network(map_identifier, topic_identifier)
        # tree.display(topic_identifier)
        if len(tree) > 1:
            nodes = 0
            edges = 1
            result = ([], [])  # The result is a tuple containing two lists of dictionaries.
            build_network(topic_identifier)
            return jsonify(result)
        else:
            return jsonify({
                "status": "error",
                "code": 404,
                "message": "No network data"
            })
    else:
        return jsonify({
            "status": "error",
            "code": 404,
            "message": "Topic not found"
        })
