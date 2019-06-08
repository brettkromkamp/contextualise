from flask import (Blueprint, session, render_template)
from flask_security import login_required, current_user

from contextualise.topic_store import get_topic_store

bp = Blueprint('map', __name__)


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
