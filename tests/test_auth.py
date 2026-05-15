def test_index_returns_200(client):
    r = client.get('/')
    assert r.status_code == 200


def test_login_page_returns_200(client):
    r = client.get('/login')
    assert r.status_code == 200


def test_registro_page_returns_200(client):
    r = client.get('/registro')
    assert r.status_code == 200


def test_login_invalid_credentials(client):
    r = client.post('/login', data={'email': 'nao@existe.com', 'senha': 'errado'})
    assert r.status_code == 401


def test_login_valid_professor(client, professor_user):
    r = client.post('/login', data={'email': professor_user.email, 'senha': 'Senha@123'},
                    follow_redirects=True)
    assert r.status_code == 200


def test_login_valid_aluno(client, aluno_user):
    r = client.post('/login', data={'email': aluno_user.email, 'senha': 'Senha@123'},
                    follow_redirects=True)
    assert r.status_code == 200


def test_logout_redirects(client):
    r = client.get('/logout', follow_redirects=True)
    assert r.status_code == 200


def test_dashboard_professor_requires_login(client):
    r = client.get('/dashboard-professor')
    assert r.status_code in (302, 200)


def test_dashboard_aluno_requires_login(client):
    r = client.get('/dashboard-aluno')
    assert r.status_code in (302, 200)
