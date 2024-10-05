"""
config.py file. Part of the Contextualise project.

This module defines project-level constants.

October 5, 2024
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import os


class Config:
    DATABASE_FILE = os.getenv("DATABASE_FILE", "contextualise.sqlite3")
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "changeme@changeme.com")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "changeme")
    EMAIL_SERVER = os.getenv("EMAIL_SERVER", "smtp.changeme.com")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER", "Change Me <changeme@changeme.com>")
    EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
    SECRET_KEY = os.getenv("SECRET_KEY", "changeme-secret-key")
    SECURITY_PASSWORD_SALT = os.getenv("SECURITY_PASSWORD_SALT", "changeme-password-salt")