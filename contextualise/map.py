"""
map.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import os
import shutil
import uuid

from flask import Blueprint, current_app, flash, render_template, request, session, url_for
from flask_security import current_user, login_required
from topicdb.core.models.collaborationmode import CollaborationMode
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from contextualise.topic_store import get_topic_store

bp = Blueprint("map", __name__)

RESOURCES_DIRECTORY = "resources"
EXTENSIONS_WHITELIST = {"png", "jpg", "jpeg"}
UNIVERSAL_SCOPE = "*"


@bp.route("/maps/")
@login_required
def index():
    store = get_topic_store()

    maps = store.get_maps(current_user.id)

    own_maps = [map for map in maps if map.owner]
    collaboration_maps = [map for map in maps if not map.owner]

    # Reset breadcrumbs and (current) scope
    session["breadcrumbs"] = []
    session["current_scope"] = UNIVERSAL_SCOPE
    session["scope_filter"] = 1

    return render_template("map/index.html", own_maps=own_maps, collaboration_maps=collaboration_maps)


@bp.route("/maps/published/")
def published():
    store = get_topic_store()

    maps = store.get_published_maps()

    # Reset breadcrumbs and (current) scope
    session["breadcrumbs"] = []
    session["current_scope"] = UNIVERSAL_SCOPE
    session["scope_filter"] = 1

    return render_template("map/published.html", maps=maps)


@bp.route("/maps/create/", methods=("GET", "POST"))
@login_required
def create():
    store = get_topic_store()

    form_map_name = ""
    form_map_description = ""
    form_map_shared = False

    error = 0

    if request.method == "POST":
        form_map_name = request.form["map-name"].strip()
        form_map_description = request.form["map-description"].strip()
        form_map_published = True if request.form.get("map-published") == "1" else False
        form_upload_file = request.files["map-image-file"] if "map-image-file" in request.files else None

        # Validate form inputs
        if not form_map_name:
            error = error | 1
        if form_upload_file:
            if form_upload_file.filename == "":
                error = error | 2
            elif not allowed_file(form_upload_file.filename):
                error = error | 4

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            image_file_name = (
                f"{str(uuid.uuid4())}.{get_file_extension(form_upload_file.filename)}" if form_upload_file else ""
            )

            # Create and initialise the topic map
            map_identifier = store.create_map(
                current_user.id,
                form_map_name,
                form_map_description,
                image_file_name,
                initialised=True,
                published=form_map_published,
                promoted=False,
            )
            if map_identifier:
                store.populate_map(map_identifier, current_user.id)

                # Create the directory for this topic map
                topic_map_directory = os.path.join(current_app.static_folder, RESOURCES_DIRECTORY, str(map_identifier))
                if not os.path.isdir(topic_map_directory):
                    os.makedirs(topic_map_directory)

                # If there is an image for the topic map then upload it to the map's directory
                if form_upload_file:
                    file_path = os.path.join(topic_map_directory, image_file_name)
                    form_upload_file.save(file_path)

                flash("Map successfully created.", "success")
            else:
                flash(
                    "An error occurred while creating the map. Get in touch with Support if the problem persists.",
                    "danger",
                )
            return redirect(url_for("map.index"))

    return render_template(
        "map/create.html",
        error=error,
        map_name=form_map_name,
        map_description=form_map_description,
        map_shared=form_map_shared,
    )


@bp.route("/maps/delete/<map_identifier>", methods=("GET", "POST"))
@login_required
def delete(map_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    if not topic_map.owner:
        abort(403)

    if request.method == "POST":
        # Remove map from topic store
        store.delete_map(map_identifier, current_user.id)

        # Delete the map's directory
        topic_map_directory = os.path.join(current_app.static_folder, RESOURCES_DIRECTORY, str(map_identifier))
        if os.path.isdir(topic_map_directory):
            shutil.rmtree(topic_map_directory)

        flash("Map successfully deleted.", "success")
        return redirect(url_for("map.index"))

    return render_template("map/delete.html", topic_map=topic_map)


@bp.route("/maps/edit/<map_identifier>", methods=("GET", "POST"))
@login_required
def edit(map_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    if not topic_map.owner:
        abort(403)

    form_map_name = topic_map.name
    form_map_description = topic_map.description
    form_map_published = topic_map.published

    error = 0

    if request.method == "POST":
        form_map_name = request.form["map-name"].strip()
        form_map_description = request.form["map-description"].strip()
        form_map_published = True if request.form.get("map-published") == "1" else False
        form_upload_file = request.files["map-image-file"] if "map-image-file" in request.files else None

        # Validate form inputs
        if not form_map_name:
            error = error | 1
        if form_upload_file:
            if form_upload_file.filename == "":
                error = error | 2
            elif not allowed_file(form_upload_file.filename):
                error = error | 4

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            if form_upload_file:
                # Upload the image for the topic map to the map's directory
                image_file_name = f"{str(uuid.uuid4())}.{get_file_extension(form_upload_file.filename)}"
                topic_map_directory = os.path.join(current_app.static_folder, RESOURCES_DIRECTORY, str(map_identifier))
                file_path = os.path.join(topic_map_directory, image_file_name)
                form_upload_file.save(file_path)

                # TODO: Remove the map's previous image
            else:
                image_file_name = topic_map.image_path

            # Update the topic map
            promoted = form_map_published and topic_map.promoted
            store.update_map(
                map_identifier,
                form_map_name,
                form_map_description,
                image_file_name,
                published=form_map_published,
                promoted=promoted,
            )
            flash("Map successfully updated.", "success")
            return redirect(url_for("map.view", map_identifier=map_identifier))

    return render_template(
        "map/edit.html",
        error=error,
        topic_map=topic_map,
        map_name=form_map_name,
        map_description=form_map_description,
        map_shared=form_map_published,
    )


@bp.route("/maps/view/<map_identifier>")
def view(map_identifier):
    store = get_topic_store()

    collaboration_mode = None
    if current_user.is_authenticated:  # User is logged in
        is_map_owner = store.is_map_owner(map_identifier, current_user.id)
        if is_map_owner:
            topic_map = store.get_map(map_identifier, current_user.id)
        else:
            topic_map = store.get_map(map_identifier)
        if topic_map is None:
            abort(404)
        collaboration_mode = store.get_collaboration_mode(map_identifier, current_user.id)
        # The map is private and doesn't belong to the user who is trying to
        # access it
        if not topic_map.published and not is_map_owner:
            if not collaboration_mode:  # The user is not collaborating on the map
                abort(403)
    else:  # User is not logged in
        topic_map = store.get_map(map_identifier)
        if topic_map is None:
            abort(404)
        if not topic_map.published:  # User is not logged in and the map is not published
            abort(403)

    return render_template("map/view.html", topic_map=topic_map)


@bp.route("/maps/collaborators/<map_identifier>", methods=("GET", "POST"))
@login_required
def collaborators(map_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    if not topic_map.owner:
        abort(403)

    collaborators = store.get_collaborators(map_identifier)  # TODO: Rename (shadows -method- name from outer scope)?

    return render_template("map/collaborators.html", topic_map=topic_map, collaborators=collaborators)


@bp.route("/maps/add-collaborator/<map_identifier>", methods=("GET", "POST"))
@login_required
def add_collaborator(map_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    if not topic_map.owner:
        abort(403)

    form_collaborator_email = ""
    form_collaboration_mode = "view"  # TODO: Review.

    error = 0

    if request.method == "POST":
        form_collaborator_email = request.form["collaborator-email"].strip()
        form_collaboration_mode = request.form["collaboration-mode"]

        collaborator = current_app.extensions["security"].datastore.find_user(email=form_collaborator_email)
        if not collaborator:
            error = error | 1
        if form_collaborator_email == current_user.email:
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            collaboration_mode = None
            if form_collaboration_mode == "edit":
                collaboration_mode = CollaborationMode.EDIT
            elif form_collaboration_mode == "comment":
                collaboration_mode = CollaborationMode.COMMENT
            else:
                collaboration_mode = CollaborationMode.VIEW
            store.collaborate(
                topic_map.identifier,
                collaborator.id,
                collaboration_mode,
            )
            flash("Collaborator successfully added.", "success")
            return redirect(url_for("map.collaborators", map_identifier=topic_map.identifier))

    return render_template(
        "map/add_collaborator.html",
        error=error,
        topic_map=topic_map,
        collaborator_email=form_collaborator_email,
        collaboration_mode=form_collaboration_mode,
    )


@bp.route(
    "/maps/delete-collaborator/<map_identifier>/<collaborator_identifier>",
    methods=("GET", "POST"),
)
@login_required
def delete_collaborator(map_identifier, collaborator_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    if not topic_map.owner:
        abort(403)
    collaborator = store.get_collaborator(map_identifier, collaborator_identifier)
    if collaborator is None:
        abort(404)

    error = 0

    if request.method == "POST":
        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            store.stop_collaboration(map_identifier, collaborator_identifier)
            flash("Collaborator successfully removed.", "success")
            return redirect(url_for("map.collaborators", map_identifier=topic_map.identifier))

    return render_template(
        "map/delete_collaborator.html",
        error=error,
        topic_map=topic_map,
        collaborator_identifier=collaborator_identifier,
        collaborator=collaborator,
    )


@bp.route(
    "/maps/edit-collaborator/<map_identifier>/<collaborator_identifier>",
    methods=("GET", "POST"),
)
@login_required
def edit_collaborator(map_identifier, collaborator_identifier):
    store = get_topic_store()

    topic_map = store.get_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    if not topic_map.owner:
        abort(403)
    collaborator = store.get_collaborator(map_identifier, collaborator_identifier)
    if collaborator is None:
        abort(404)

    form_collaboration_mode = collaborator.collaboration_mode.name.lower()
    form_collaborator_email = collaborator.user_name

    error = 0

    if request.method == "POST":
        form_collaboration_mode = request.form["collaboration-mode"]
        form_collaborator_email = request.form["collaborator-email"]

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            store.update_collaboration_mode(
                map_identifier,
                collaborator_identifier,
                CollaborationMode[form_collaboration_mode.upper()],
            )
            flash("Collaborator successfully updated.", "success")
            return redirect(url_for("map.collaborators", map_identifier=topic_map.identifier))

    return render_template(
        "map/edit_collaborator.html",
        error=error,
        topic_map=topic_map,
        collaborator_identifier=collaborator_identifier,
        collaborator_email=form_collaborator_email,
        collaboration_mode=form_collaboration_mode,
    )


# ========== HELPER METHODS ==========


def get_file_extension(file_name):
    return file_name.rsplit(".", 1)[1].lower()


def allowed_file(file_name):
    return get_file_extension(file_name) in EXTENSIONS_WHITELIST
