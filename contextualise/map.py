from flask import (Blueprint, session, request, render_template)
from flask_security import login_required, current_user

from contextualise.topic_store import get_topic_store

bp = Blueprint('map', __name__)

RESOURCES_DIRECTORY = 'static/resources/'
EXTENSIONS_WHITELIST = {'png', 'jpg', 'jpeg', 'gif'}


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


@bp.route('/maps/create/')
@login_required
def create():
    topic_store = get_topic_store()

    form_name = ''
    form_description = ''
    form_shared = False

    error = 0

    if request.method == 'POST':
        pass

    return render_template('map/create.html',
                           error=error,
                           map_name=form_name,
                           map_description=form_description,
                           map_shared=form_shared)


# ========== HELPER METHODS ==========

def get_file_extension(file_name):
    return file_name.rsplit('.', 1)[1].lower()


def allowed_file(file_name):
    return get_file_extension(file_name) in EXTENSIONS_WHITELIST
