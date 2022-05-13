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
from flask_seasurf import SeaSurf
from flask_security import (
    RoleMixin,
    Security,
    SQLAlchemySessionUserDatastore,
    UserMixin,
    hash_password,
    user_authenticated,
    user_registered,
)
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, scoped_session, sessionmaker

from contextualise.topic_store import get_topic_store
from contextualise.utilities import filters

from .version import __version__

UNIVERSAL_SCOPE = "*"

# Application factory function
def create_app(test_config=None):
    # Create app
    app = Flask(__name__, instance_relative_config=True)
    app.version = __version__

    # Configure app
    app.config.from_object("contextualise.settings")
    app.config.from_envvar("CONTEXTUALISE_SETTINGS")
    app.config.from_mapping(
        DEBUG=False,
        DATABASE_PATH=os.path.join(app.instance_path, app.config["DATABASE_FILE"]),
        SECRET_KEY=os.environ.get("SECRET_KEY", "ppBcUQ5AL7gEmvb0blMDyEOpiBEQUupGmk_a3DMaF34"),
        SECURITY_PASSWORD_SALT=os.environ.get("SECURITY_PASSWORD_SALT", "139687009245803364536588051620840970665"),
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

    # Set up app
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
        maps = get_topic_store().get_promoted_maps()
        maps = [map for map in maps if map.published]

        # Reset breadcrumbs and (current) scope
        session["breadcrumbs"] = []
        session["current_scope"] = UNIVERSAL_SCOPE
        session["scope_filter"] = 1

        return render_template("index.html", maps=maps, version=app.version)

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

    @user_registered.connect_via(app)
    def user_registered_handler(app, user, confirm_token, form_data, **extra_args):
        default_role = user_datastore.find_role("user")
        user_datastore.add_role_to_user(user, default_role)
        db_session.commit()

    @user_authenticated.connect_via(app)
    def user_authenticated_handler(app, user, authn_via, **extra_args):
        app.logger.info(f"User logged in successfully: [{user.email}], authentication method: [{authn_via}]")

    @app.before_first_request
    def create_user():
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

    @app.teardown_request
    def checkin_db(exc):
        db_session.remove()

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

    # Set up logging
    if not app.debug:
        logs_directory = os.path.join(app.instance_path, "logs")
        if not os.path.exists(logs_directory):
            os.mkdir(logs_directory)
        file_handler = RotatingFileHandler(
            os.path.join(logs_directory, "contextualise.log"), maxBytes=10240, backupCount=10
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
    app = create_app()
    app.run(
        debug=True,
        use_debugger=False,
        use_reloader=False,
        passthrough_errors=True,
        host="0.0.0.0",
    )
