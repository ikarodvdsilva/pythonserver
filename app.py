import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from models import db
from routes import api
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configurar CORS
    CORS(app)
    
    # Inicializar banco de dados
    db.init_app(app)
    
    # Configurar migrações
    migrate = Migrate(app, db)
    
    # Registrar blueprint da API
    app.register_blueprint(api, url_prefix='/api')
    
    # Criar pasta de uploads se não existir
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    @app.route('/')
    def index():
        return {
            'message': 'API de Denúncias Ambientais',
            'version': '1.0.0',
            'status': 'online'
        }
     
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
