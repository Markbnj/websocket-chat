"""Olark homework chat service.

..  module:: config/__init__.py
    :platform: linux
    :synopsis: provides access to the settings in config/settings.json.

..  moduleauthor:: Mark Betz <betz.mark@gmail.com>

"""
import json
import os


settings = None


current_dir = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(current_dir, "settings.json"), "rb") as f:
    settings = json.loads(f.read())
