import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, current_app
from werkzeug.utils import secure_filename
from . import bp
from ...extensions import db
from ...models import (Professor, Atividade, Aluno, PerfilAprendizagem,
                       Usuario, TrilhaAprendizado, BibliotecaConteudo)


def _professor_required():
    if 'usuario_id' not in session or session.get('tipo') != 'professor':
        return redirect(url_for('auth.login'))
    return None


@bp.route('/dashboard-professor')
def dashboard_professor():
    r = _professor_required()
    if r:
        return r
    professor = Professor.query.filter_by(usuario_id=session['usuario_id']).first()
    atividades = Atividade.query.filter_by(professor_id=professor.id).all()
    return render_template('dashboard_professor.html', atividades=atividades)


@bp.route('/alunos')
def listar_alunos():
    r = _professor_required()
    if r:
        return r
    alunos = Aluno.query.all()
    return render_template('listar_alunos.html', alunos=alunos)


@bp.route('/painel-professor')
def painel_professor():
    r = _professor_required()
    if r:
        return r
    tipo_filtro = request.args.get('tipo_perfil', '')
    query = db.session.query(Aluno, PerfilAprendizagem).join(
        PerfilAprendizagem, Aluno.id == PerfilAprendizagem.aluno_id, isouter=True
    ).join(Usuario, Aluno.usuario_id == Usuario.id)
    if tipo_filtro:
        query = query.filter(PerfilAprendizagem.tipo_perfil.like(f'%{tipo_filtro}%'))
    alunos_perfis = query.all()
    tipos_perfil = [t[0] for t in db.session.query(PerfilAprendizagem.tipo_perfil).distinct().all() if t[0]]
    return render_template('painel_professor.html', alunos_perfis=alunos_perfis,
                           tipos_perfil=tipos_perfil, tipo_filtro=tipo_filtro)


@bp.route('/criar-atividade', methods=['GET', 'POST'])
def criar_atividade():
    r = _professor_required()
    if r:
        return r
    if request.method == 'POST':
        professor = Professor.query.filter_by(usuario_id=session['usuario_id']).first()
        data_limite = None
        if request.form.get('data_limite'):
            data_limite = datetime.strptime(request.form['data_limite'], '%Y-%m-%dT%H:%M')

        arquivo_anexo = None
        arquivo_original = None
        if 'arquivo' in request.files:
            arquivo = request.files['arquivo']
            if arquivo and arquivo.filename != '':
                upload_folder = os.path.join(current_app.root_path, '..', 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                arquivo_original = arquivo.filename
                nome_arquivo = f"atividade_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(arquivo.filename)}"
                arquivo_anexo = nome_arquivo
                arquivo.save(os.path.join(upload_folder, nome_arquivo))

        atividade = Atividade(
            titulo=request.form['titulo'],
            descricao=request.form['descricao'],
            tipo=request.form['tipo'],
            professor_id=professor.id,
            data_limite=data_limite,
            arquivo_anexo=arquivo_anexo,
            arquivo_original=arquivo_original,
            pontuacao_maxima=int(request.form.get('pontuacao_maxima', 100)),
            instrucoes_especiais=request.form.get('instrucoes_especiais', '')
        )
        db.session.add(atividade)
        db.session.commit()
        return redirect(url_for('professor.dashboard_professor'))

    return render_template('criar_atividade.html')


@bp.route('/criar-trilha', methods=['GET', 'POST'])
def criar_trilha():
    r = _professor_required()
    if r:
        return r
    if request.method == 'POST':
        trilha = TrilhaAprendizado(
            nome=request.form['nome'],
            descricao=request.form['descricao'],
            tipo_conteudo=request.form['tipo_conteudo'],
            nivel_dificuldade=request.form['nivel_dificuldade'],
            area_conhecimento=request.form['area_conhecimento'],
            perfil_alvo=request.form.get('perfil_alvo', ''),
            duracao_estimada=int(request.form.get('duracao_estimada', 0)),
            url_conteudo=request.form.get('url_conteudo', ''),
            arquivo_conteudo=request.form.get('arquivo_conteudo', '')
        )
        db.session.add(trilha)
        db.session.commit()
        return redirect(url_for('aluno.trilhas_aprendizado'))
    return render_template('criar_trilha.html')


@bp.route('/adicionar-conteudo-biblioteca', methods=['GET', 'POST'])
def adicionar_conteudo_biblioteca():
    r = _professor_required()
    if r:
        return r
    if request.method == 'POST':
        conteudo = BibliotecaConteudo(
            titulo=request.form['titulo'],
            descricao=request.form['descricao'],
            tipo=request.form['tipo'],
            categoria=request.form['categoria'],
            nivel_ensino=request.form.get('nivel_ensino', ''),
            url_conteudo=request.form.get('url_conteudo', ''),
            arquivo_conteudo=request.form.get('arquivo_conteudo', ''),
            tem_legenda=bool(request.form.get('tem_legenda')),
            tem_libras=bool(request.form.get('tem_libras')),
            tem_transcricao=request.form.get('tem_transcricao', ''),
            duracao=int(request.form.get('duracao', 0)) if request.form.get('duracao') else None,
            classificacao_etaria=request.form.get('classificacao_etaria', 'livre'),
            tags=request.form.get('tags', '')
        )
        db.session.add(conteudo)
        db.session.commit()
        return redirect(url_for('aluno.biblioteca'))
    return render_template('adicionar_conteudo_biblioteca.html')
