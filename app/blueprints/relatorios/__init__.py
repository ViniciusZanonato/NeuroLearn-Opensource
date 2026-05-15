from flask import Blueprint

bp = Blueprint('relatorios', __name__)

from . import routes  # noqa: F401, E402
