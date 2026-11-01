"""ASGI entry: uvicorn royexa.main:app"""

from royexa.api import create_app
from royexa.bootstrap import Settings, build_container

app = create_app(build_container(Settings.from_env()))
