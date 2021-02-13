"""
__init__.py file. Part of the Contextualise project.

March 4, 2019
Brett Alistair Kromkamp (brett.kromkamp@gmail.com)
"""

import configparser
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, session, render_template
from flask_mail import Mail
from flask_seasurf import SeaSurf
from flask_security import (
    Security,
    SQLAlchemySessionUserDatastore,
    user_registered,
    user_authenticated,
    hash_password,
)

from contextualise.security import user_store, user_models
from contextualise.utilities import filters

from contextualise.topic_store import get_topic_store

UNIVERSAL_SCOPE = "*"
SETTINGS_FILE_PATH = os.path.join(os.path.dirname(__file__), "../settings.ini")

config = configparser.ConfigParser()
config.read(SETTINGS_FILE_PATH)

database_username = config["DATABASE"]["Username"]
database_password = config["DATABASE"]["Password"]
database_name = config["DATABASE"]["Database"]
database_host = config["DATABASE"]["Host"]
database_port = config["DATABASE"]["Port"]
email_username = config["EMAIL"]["Username"]
email_password = config["EMAIL"]["Password"]
email_server = config["EMAIL"]["Server"]
email_sender = config["EMAIL"]["Sender"]


# Application factory function
def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DEBUG=False,
        SECRET_KEY=os.environ.get("SECRET_KEY", "ppBcUQ5AL7gEmvb0blMDyEOpiBEQUupGmk_a3DMaF34"),
        TOPIC_STORE_USER=database_username,
        TOPIC_STORE_PASSWORD=database_password,
        TOPIC_STORE_DBNAME=database_name,
        TOPIC_STORE_HOST=database_host,
        TOPIC_STORE_PORT=database_port,
        SECURITY_PASSWORD_SALT=os.environ.get("SECURITY_PASSWORD_SALT", "139687009245803364536588051620840970665"),
        SECURITY_REGISTERABLE=True,
        SECURITY_RECOVERABLE=True,
        SECURITY_EMAIL_SENDER=email_sender,
        SECURITY_URL_PREFIX="/auth",
        SECURITY_POST_LOGIN_VIEW="/maps/",
        SECURITY_POST_REGISTER_VIEW="/maps/",
        MAIL_SERVER=email_server,
        MAIL_PORT=587,
        MAIL_USE_SSL=False,
        MAIL_USERNAME=email_username,
        MAIL_PASSWORD=email_password,
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
        # 4 megabytes (temporarily - will be 2)
    )
    mail = Mail(app)
    csrf = SeaSurf(app)

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route("/")
    def home():
        maps = get_topic_store().get_promoted_topic_maps()

        # Reset breadcrumbs and (current) scope
        session["breadcrumbs"] = []
        session["current_scope"] = UNIVERSAL_SCOPE
        session["scope_filter"] = 1

        return render_template("index.html", maps=maps)

    @app.route("/health")
    def hello():
        return "Healthy!"

    # HTTP error handlers
    def forbidden(e):
        return render_template("403.html"), 403

    app.register_error_handler(403, forbidden)

    def page_not_found(e):
        return render_template("404.html"), 404

    app.register_error_handler(404, page_not_found)

    def internal_server_error(e):
        return render_template("500.html"), 500

    app.register_error_handler(500, internal_server_error)

    def request_entity_too_large(e):
        return render_template("413.html"), 413

    app.register_error_handler(413, request_entity_too_large)

    # Setup Flask-Security
    user_datastore = SQLAlchemySessionUserDatastore(user_store.db_session, user_models.User, user_models.Role)
    security = Security(app, user_datastore)

    @user_registered.connect_via(app)
    def user_registered_handler(app, user, confirm_token, form_data, **extra_args):
        default_role = user_datastore.find_role("user")
        user_datastore.add_role_to_user(user, default_role)
        user_store.db_session.commit()

    @user_authenticated.connect_via(app)
    def user_authenticated_handler(app, user, authn_via, **extra_args):
        app.logger.info(f"User logged in successfully: [{user.email}], authentication method: [{authn_via}]")

    @app.before_first_request
    def create_user():
        user_store.init_db()

        # Create roles
        admin_role = user_datastore.find_or_create_role(name="admin", description="Administrator")
        user_role = user_datastore.find_or_create_role(name="user", description="End user")

        # Create users
        admin_user = user_datastore.find_user(email="admin@contextualise.dev")
        if not admin_user:
            admin_user = user_datastore.create_user(
                email="admin@contextualise.dev", password=hash_password("Passw0rd1")
            )

        user_user = user_datastore.find_user(email="user@contextualise.dev")
        if not user_user:
            user_datastore.create_user(email="user@contextualise.dev", password=hash_password("Passw0rd1"))
        user_store.db_session.commit()

        # Assign roles
        user_datastore.add_role_to_user(user_user, user_role)
        user_datastore.add_role_to_user(admin_user, admin_role)
        user_store.db_session.commit()

    @app.teardown_request
    def checkin_db(exc):
        user_store.db_session.remove()

    # Register custom filters
    filters.register_filters(app)

    # Register Blueprints
    from contextualise import api

    app.register_blueprint(api.bp)
    csrf.exempt(api.create_topic)
    csrf.exempt(api.create_association)

    from contextualise import map

    app.register_blueprint(map.bp)

    from contextualise import topic

    app.register_blueprint(topic.bp)

    from contextualise import image

    app.register_blueprint(image.bp)

    from contextualise import file

    app.register_blueprint(file.bp)

    from contextualise import link

    app.register_blueprint(link.bp)

    from contextualise import video

    app.register_blueprint(video.bp)

    from contextualise import association

    app.register_blueprint(association.bp)

    from contextualise import note

    app.register_blueprint(note.bp)

    from contextualise import three_d

    app.register_blueprint(three_d.bp)

    from contextualise import attribute

    app.register_blueprint(attribute.bp)

    from contextualise import visualisation

    app.register_blueprint(visualisation.bp)

    from contextualise import tag

    app.register_blueprint(tag.bp)

    # Add topic store
    # from contextualise import topic_store

    # topic_store.init_app(app)

    # Set up logging
    if not app.debug:
        if not os.path.exists("logs"):
            os.mkdir("logs")
        file_handler = RotatingFileHandler("logs/contextualise.log", maxBytes=10240, backupCount=10)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
        )
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("Contextualise startup")

    return app


# For debugging purposes (inside PyCharm)
if __name__ == "__main__":
    app = create_app()
    app.run(
        debug=True,
        use_debugger=False,
        use_reloader=False,
        passthrough_errors=True,
        host="0.0.0.0",
    )
