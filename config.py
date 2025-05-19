import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    # Configuração do banco de dados
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuração do JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    
    # Configuração de upload de arquivos
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Configuração do Flask
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
 