"""
__init__.py file. Part of the Contextualise project.

March 4, 2019
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, session
from flask_mail import Mail
from flask_security.core import RoleMixin, Security, UserMixin
from flask_security.datastore import SQLAlchemySessionUserDatastore
from flask_security.signals import user_authenticated, user_registered
from flask_security.utils import hash_password
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, scoped_session, sessionmaker

from . import constants
from .topic_store import get_topic_store
from .utilities import filters
from .version import __version__


# Application factory function
def create_app(test_config=None):
    # Create app
    app = Flask(__name__, instance_relative_config=True)
    app.config["version"] = __version__

    # Configure app
    app.config.from_object("contextualise.config.Config")
    app.config.from_mapping(
        DEBUG=False,
        DATABASE_PATH=os.path.join(app.instance_path, app.config["DATABASE_FILE"]),
        SECRET_KEY=app.config["SECRET_KEY"],
        SECURITY_PASSWORD_SALT=app.config["SECURITY_PASSWORD_SALT"],
        SECURITY_REGISTERABLE=True,
        SECURITY_RECOVERABLE=True,
        SECURITY_URL_PREFIX="/auth",
        SECURITY_POST_LOGIN_VIEW="/maps/",
        SECURITY_POST_REGISTER_VIEW="/maps/",
        MAIL_SERVER=app.config["EMAIL_SERVER"],
        MAIL_PORT=app.config["EMAIL_PORT"],
        MAIL_USERNAME=app.config["EMAIL_USERNAME"],
        MAIL_PASSWORD=app.config["EMAIL_PASSWORD"],
        MAIL_DEFAULT_SENDER=app.config["EMAIL_SENDER"],
        MAIL_USE_SSL=False,
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,  # 4 megabytes
    )
    app.config["REMEMBER_COOKIE_SAMESITE"] = "strict"
    app.config["SESSION_COOKIE_SAMESITE"] = "strict"

    # Set up app
    mail = Mail(app)
    csrf = CSRFProtect(app)

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
        promoted_maps = get_topic_store().get_promoted_maps()
        promoted_maps = [promoted_map for promoted_map in promoted_maps if promoted_map.published]

        # Reset breadcrumbs and (current) scope
        session["breadcrumbs"] = []
        session["current_scope"] = constants.UNIVERSAL_SCOPE
        session["scope_filter"] = 1

        return render_template("index.html", maps=promoted_maps, version=app.config["version"])

    @app.route("/health")
    def health():
        return "Healthy!"

    # HTTP error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template("413.html"), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html"), 500

    # Setup Flask-Security
    engine = create_engine(f"sqlite:///{app.config['DATABASE_PATH']}")
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

    Base = declarative_base()
    Base.query = db_session.query_property()

    class RolesUsers(Base):
        __tablename__ = "roles_users"
        id = Column(Integer(), primary_key=True)
        user_id = Column("user_id", Integer(), ForeignKey("user.id"))
        role_id = Column("role_id", Integer(), ForeignKey("role.id"))

    class Role(Base, RoleMixin):
        __tablename__ = "role"
        id = Column(Integer(), primary_key=True)
        name = Column(String(80), unique=True)
        description = Column(String(255))

    class User(Base, UserMixin):
        __tablename__ = "user"
        id = Column(Integer, primary_key=True)
        email = Column(String(255), unique=True)
        username = Column(String(255), unique=True, nullable=True)
        password = Column(String(255), nullable=False)
        last_login_at = Column(DateTime())
        current_login_at = Column(DateTime())
        last_login_ip = Column(String(100))
        current_login_ip = Column(String(100))
        login_count = Column(Integer)
        active = Column(Boolean())
        fs_uniquifier = Column(String(255), unique=True, nullable=False)
        confirmed_at = Column(DateTime())
        roles = relationship("Role", secondary="roles_users", backref=backref("users", lazy="dynamic"))

    user_datastore = SQLAlchemySessionUserDatastore(db_session, User, Role)
    security = Security(app, user_datastore)

    with app.app_context():
        Base.metadata.create_all(bind=engine)
        # Create roles
        admin_role = user_datastore.find_or_create_role(name="admin", description="Administrator")
        user_role = user_datastore.find_or_create_role(name="user", description="End user")
        db_session.commit()

        # Create users
        admin_user = user_datastore.find_user(email="admin@contextualise.dev")
        if not admin_user:
            admin_user = user_datastore.create_user(
                email="admin@contextualise.dev", password=hash_password("Passw0rd1")
            )
            db_session.commit()
        user_user = user_datastore.find_user(email="user@contextualise.dev")
        if not user_user:
            user_user = user_datastore.create_user(email="user@contextualise.dev", password=hash_password("Passw0rd1"))
            db_session.commit()

        # Assign roles
        user_datastore.add_role_to_user(user_user, user_role)
        user_datastore.add_role_to_user(admin_user, admin_role)
        db_session.commit()

        # Create database structure
        get_topic_store().create_database()

    @user_registered.connect_via(app)
    def user_registered_handler(app, user, confirm_token, form_data, **extra_args):
        default_role = user_datastore.find_role("user")
        user_datastore.add_role_to_user(user, default_role)
        db_session.commit()

    @user_authenticated.connect_via(app)
    def user_authenticated_handler(app, user, authn_via, **extra_args):
        app.logger.info(f"User logged in successfully: [{user.email}], authentication method: [{authn_via}]")

    @app.teardown_request
    def checkin_db(exc):
        db_session.remove()

    # Register custom filters
    filters.register_filters(app)

    # Register Blueprints
    import contextualise.api

    app.register_blueprint(contextualise.api.bp)
    csrf.exempt(contextualise.api.create_topic)
    csrf.exempt(contextualise.api.create_association)

    import contextualise.map

    app.register_blueprint(contextualise.map.bp)

    import contextualise.topic

    app.register_blueprint(contextualise.topic.bp)

    import contextualise.image

    app.register_blueprint(contextualise.image.bp)

    import contextualise.file

    app.register_blueprint(contextualise.file.bp)

    import contextualise.link

    app.register_blueprint(contextualise.link.bp)

    import contextualise.video

    app.register_blueprint(contextualise.video.bp)

    import contextualise.association

    app.register_blueprint(contextualise.association.bp)

    import contextualise.note

    app.register_blueprint(contextualise.note.bp)

    import contextualise.three_d

    app.register_blueprint(contextualise.three_d.bp)

    import contextualise.attribute

    app.register_blueprint(contextualise.attribute.bp)

    import contextualise.visualisation

    app.register_blueprint(contextualise.visualisation.bp)

    import contextualise.tag

    app.register_blueprint(contextualise.tag.bp)

    # Set up logging
    if not app.debug:
        logs_directory = os.path.join(app.instance_path, "logs")
        if not os.path.exists(logs_directory):
            os.mkdir(logs_directory)
        file_handler = RotatingFileHandler(
            os.path.join(logs_directory, "contextualise.log"),
            maxBytes=10240,
            backupCount=10,
        )
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
    flask_app = create_app()
    flask_app.run(
        debug=True,
        use_debugger=False,
        use_reloader=False,
        passthrough_errors=True,
        host="0.0.0.0",
    )
