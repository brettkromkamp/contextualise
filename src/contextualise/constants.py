"""
constants.py file. Part of the Contextualise project.

This module defines project-level constants.

July 28, 2024
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import os

UNIVERSAL_SCOPE = "*"
SETTINGS_FILE_PATH = os.path.join(os.path.dirname(__file__), "../settings.ini")
RESOURCES_DIRECTORY = "resources"
IMAGE_EXTENSIONS_WHITELIST = {"png", "jpg", "jpeg", "gif"}
THREE_D_EXTENSIONS_WHITELIST = {"gltf", "glb"}
BREADCRUMBS_COUNT = 5
RESPONSE = 0
STATUS_CODE = 1
MAP_ITEMS_PER_PAGE = 9
TOPIC_ITEMS_PER_PAGE = 25
RESOURCE_ITEMS_PER_PAGE = 25
