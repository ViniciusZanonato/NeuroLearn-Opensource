from flask import Blueprint

bp = Blueprint('professor', __name__)

from . import routes  # noqa: F401, E402
