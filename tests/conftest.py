import pytest
from app import create_app
from app.extensions import db as _db
from app.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'
    SESSION_COOKIE_SECURE = False
    AI_PROVIDER = 'ollama'


@pytest.fixture(scope='session')
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()


_counter = {'n': 0}


def _next():
    _counter['n'] += 1
    return _counter['n']


@pytest.fixture
def professor_user(db):
    from werkzeug.security import generate_password_hash
    from app.models import Usuario, Professor
    n = _next()
    u = Usuario(nome=f'Prof Teste {n}', email=f'prof{n}@test.com',
                senha_hash=generate_password_hash('Senha@123'), tipo='professor')
    db.session.add(u)
    db.session.flush()
    p = Professor(usuario_id=u.id, disciplina='Matemática')
    db.session.add(p)
    db.session.commit()
    return u


@pytest.fixture
def aluno_user(db):
    from werkzeug.security import generate_password_hash
    from app.models import Usuario, Aluno
    n = _next()
    u = Usuario(nome=f'Aluno Teste {n}', email=f'aluno{n}@test.com',
                senha_hash=generate_password_hash('Senha@123'), tipo='aluno')
    db.session.add(u)
    db.session.flush()
    a = Aluno(usuario_id=u.id, serie_ano='7 Ano', professor_responsavel='Prof Teste',
              idade=13, questionario_completo=False)
    db.session.add(a)
    db.session.commit()
    return u
