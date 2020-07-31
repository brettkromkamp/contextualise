from flask import Blueprint, session, flash, render_template, request, url_for, redirect
from flask_security import login_required, current_user

from contextualise.topic_store import get_topic_store

bp = Blueprint("tag", __name__)


@bp.route("/tags/add/<map_identifier>", methods=("GET", "POST"))
@login_required
def add(map_identifier):
    pass
