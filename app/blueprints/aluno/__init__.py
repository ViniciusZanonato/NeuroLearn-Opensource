from flask import Blueprint

bp = Blueprint('aluno', __name__)

from . import routes  # noqa: F401, E402
