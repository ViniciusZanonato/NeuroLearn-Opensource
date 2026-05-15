from app import create_app
from app.extensions import db
from app.models import Usuario, Aluno, Professor, QuestionarioNeuroLearn, PerfilAprendizagem, Atividade, RespostaAluno, AnaliseIA

app = create_app()
from werkzeug.security import generate_password_hash

def init_database():
    with app.app_context():
        # Apagar todas as tabelas
        db.drop_all()
        
        # Criar todas as tabelas novamente
        db.create_all()
        
        # Criar usuários de teste
        # Professor de teste
        professor_user = Usuario(
            nome="Prof. Ana Silva",
            email="professor@test.com",
            senha_hash=generate_password_hash("123456"),
            tipo="professor"
        )
        db.session.add(professor_user)
        db.session.commit()
        
        professor = Professor(
            usuario_id=professor_user.id,
            disciplina="Matemática e Ciências",
            formacao="Licenciatura em Matemática"
        )
        db.session.add(professor)
        
        # Aluno de teste
        aluno_user = Usuario(
            nome="João Santos",
            email="aluno@test.com",
            senha_hash=generate_password_hash("123456"),
            tipo="aluno"
        )
        db.session.add(aluno_user)
        db.session.commit()
        
        aluno = Aluno(
            usuario_id=aluno_user.id,
            email_escola="joao.santos@escola.edu.br",
            serie_ano="7º Ano - Fundamental",
            professor_responsavel="Prof. Ana Silva",
            idade=13,
            questionario_completo=False,
            perfil_gerado=False
        )
        db.session.add(aluno)
        
        db.session.commit()
        
        print("Banco de dados inicializado com sucesso!")
        print("Usuários criados:")
        print("Professor: professor@test.com / 123456")
        print("Aluno: aluno@test.com / 123456")

if __name__ == '__main__':
    init_database()

