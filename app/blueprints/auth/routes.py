from flask import render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from . import bp
from ...extensions import db
from ...models import Usuario, Aluno, Professor
from ...utils.monitoring import registrar_monitoramento


@bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        tipo = request.form['tipo']

        if Usuario.query.filter_by(email=email).first():
            return jsonify({'erro': 'Email já cadastrado'}), 400

        novo_usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=generate_password_hash(senha),
            tipo=tipo
        )
        db.session.add(novo_usuario)
        db.session.commit()

        if tipo == 'aluno':
            aluno = Aluno(
                usuario_id=novo_usuario.id,
                email_escola=request.form.get('email_escola'),
                serie_ano=request.form.get('serie_ano'),
                professor_responsavel=request.form.get('professor_responsavel'),
                idade=int(request.form.get('idade'))
            )
            db.session.add(aluno)
        else:
            professor = Professor(
                usuario_id=novo_usuario.id,
                disciplina=request.form.get('disciplina'),
                formacao=request.form.get('formacao')
            )
            db.session.add(professor)

        db.session.commit()
        session['usuario_id'] = novo_usuario.id
        session['tipo'] = novo_usuario.tipo
        return jsonify({'sucesso': 'Usuário registrado com sucesso'})

    return render_template('registro.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.senha_hash, senha):
            session['usuario_id'] = usuario.id
            session['tipo'] = usuario.tipo

            if usuario.tipo == 'aluno':
                aluno = Aluno.query.filter_by(usuario_id=usuario.id).first()
                if aluno:
                    registrar_monitoramento(aluno.id, 'login', 'sistema')

            if usuario.tipo == 'professor':
                return redirect(url_for('professor.dashboard_professor'))
            else:
                return redirect(url_for('aluno.dashboard_aluno'))
        else:
            return jsonify({'erro': 'Credenciais inválidas'}), 401

    return render_template('login.html')


@bp.route('/logout')
def logout():
    if 'usuario_id' in session and session['tipo'] == 'aluno':
        aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        if aluno:
            registrar_monitoramento(aluno.id, 'logout', 'sistema')
    session.clear()
    return redirect(url_for('main.index'))
