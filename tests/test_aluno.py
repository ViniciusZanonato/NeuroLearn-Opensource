def _login(client, user):
    client.post('/login', data={'email': user.email, 'senha': 'Senha@123'})


def test_dashboard_aluno_redirects_without_login(client):
    r = client.get('/dashboard-aluno')
    assert r.status_code == 302
    assert '/login' in r.headers['Location']


def test_dashboard_aluno_redirects_to_questionario(client, aluno_user):
    _login(client, aluno_user)
    r = client.get('/dashboard-aluno')
    # aluno_user has questionario_completo=False, should redirect to questionario
    assert r.status_code == 302


def test_questionario_loads_for_aluno(client, aluno_user):
    _login(client, aluno_user)
    r = client.get('/questionario-neurolearn')
    assert r.status_code == 200


def test_questionario_requires_login(client):
    r = client.get('/questionario-neurolearn')
    assert r.status_code == 302


def test_trilhas_requires_login(client):
    r = client.get('/trilhas-aprendizado')
    assert r.status_code == 302


def test_cronograma_requires_login(client):
    r = client.get('/cronograma-estudos')
    assert r.status_code == 302


def test_assistente_requires_login(client):
    r = client.get('/assistente-virtual')
    assert r.status_code == 302


def test_acessibilidade_requires_login(client):
    r = client.get('/configuracoes-acessibilidade')
    assert r.status_code == 302


def test_biblioteca_requires_login(client):
    r = client.get('/biblioteca')
    assert r.status_code == 302


def test_biblioteca_loads_with_login(client, aluno_user):
    _login(client, aluno_user)
    r = client.get('/biblioteca')
    assert r.status_code == 200
