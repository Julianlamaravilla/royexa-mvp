"""ASGI entry: uvicorn royexa.main:app"""

from royexa.api import create_app
from royexa.bootstrap import Settings, build_container

settings = Settings.from_env()
app = create_app(build_container(settings), dispatch_every=settings.dispatch_seconds)
