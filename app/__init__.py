import os
from flask import Flask
from .config import Config
from .extensions import db


def create_app(config_class=Config):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config_class)

    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')

    db.init_app(app)

    from .blueprints.main import bp as main_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.professor import bp as professor_bp
    from .blueprints.aluno import bp as aluno_bp
    from .blueprints.relatorios import bp as relatorios_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(professor_bp)
    app.register_blueprint(aluno_bp)
    app.register_blueprint(relatorios_bp)

    with app.app_context():
        db.create_all()

    return app
