from werkzeug.security import generate_password_hash
from app.models import (Usuario, Aluno, Professor, Atividade, RespostaAluno,
                        QuestionarioNeuroLearn, PerfilAprendizagem,
                        TrilhaAprendizado, CronogramaEstudo, BibliotecaConteudo)
from datetime import date


def test_create_usuario(db):
    u = Usuario(nome='Test', email='unique@test.com',
                senha_hash=generate_password_hash('pass'), tipo='aluno')
    db.session.add(u)
    db.session.commit()
    assert u.id is not None
    assert u.nome == 'Test'


def test_create_aluno_with_usuario(db):
    u = Usuario(nome='Aluno Model', email='alunomodel@test.com',
                senha_hash=generate_password_hash('pass'), tipo='aluno')
    db.session.add(u)
    db.session.flush()
    a = Aluno(usuario_id=u.id, serie_ano='8 Ano',
              professor_responsavel='Prof', idade=14)
    db.session.add(a)
    db.session.commit()
    assert a.id is not None
    assert a.usuario.nome == 'Aluno Model'


def test_create_professor(db):
    u = Usuario(nome='Prof Model', email='profmodel@test.com',
                senha_hash=generate_password_hash('pass'), tipo='professor')
    db.session.add(u)
    db.session.flush()
    p = Professor(usuario_id=u.id, disciplina='Física')
    db.session.add(p)
    db.session.commit()
    assert p.id is not None


def test_create_atividade(db):
    u = Usuario(nome='Prof Atv', email='profatv@test.com',
                senha_hash=generate_password_hash('pass'), tipo='professor')
    db.session.add(u)
    db.session.flush()
    p = Professor(usuario_id=u.id)
    db.session.add(p)
    db.session.flush()
    atv = Atividade(titulo='Teste', descricao='Descricao', tipo='logica',
                    professor_id=p.id)
    db.session.add(atv)
    db.session.commit()
    assert atv.id is not None


def test_create_trilha(db):
    t = TrilhaAprendizado(nome='Trilha Test', tipo_conteudo='texto',
                          nivel_dificuldade='facil', area_conhecimento='matematica')
    db.session.add(t)
    db.session.commit()
    assert t.id is not None


def test_create_biblioteca_conteudo(db):
    c = BibliotecaConteudo(titulo='Video Test', tipo='video', categoria='matematica')
    db.session.add(c)
    db.session.commit()
    assert c.id is not None


def test_perfil_aprendizagem_relationship(db):
    u = Usuario(nome='Aluno Perfil', email='alunoperfil@test.com',
                senha_hash=generate_password_hash('pass'), tipo='aluno')
    db.session.add(u)
    db.session.flush()
    a = Aluno(usuario_id=u.id, serie_ano='9 Ano',
              professor_responsavel='Prof', idade=15)
    db.session.add(a)
    db.session.flush()
    p = PerfilAprendizagem(aluno_id=a.id, perfil_geral='Teste',
                           tipo_perfil='Criativo')
    db.session.add(p)
    db.session.commit()
    assert p.aluno.usuario.nome == 'Aluno Perfil'
