def _login(client, user):
    client.post('/login', data={'email': user.email, 'senha': 'Senha@123'})


def test_dashboard_professor_redirects_without_login(client):
    r = client.get('/dashboard-professor')
    assert r.status_code == 302
    assert '/login' in r.headers['Location']


def test_dashboard_professor_loads_with_login(client, professor_user):
    _login(client, professor_user)
    r = client.get('/dashboard-professor')
    assert r.status_code == 200


def test_criar_atividade_requires_professor(client):
    r = client.get('/criar-atividade')
    assert r.status_code == 302


def test_criar_atividade_page_loads(client, professor_user):
    _login(client, professor_user)
    r = client.get('/criar-atividade')
    assert r.status_code == 200


def test_listar_alunos_requires_professor(client):
    r = client.get('/alunos')
    assert r.status_code == 302


def test_listar_alunos_loads(client, professor_user):
    _login(client, professor_user)
    r = client.get('/alunos')
    assert r.status_code == 200


def test_painel_professor_loads(client, professor_user):
    _login(client, professor_user)
    r = client.get('/painel-professor')
    assert r.status_code == 200


def test_criar_trilha_page_loads(client, professor_user):
    _login(client, professor_user)
    r = client.get('/criar-trilha')
    assert r.status_code == 200
