#!/bin/bash

# Criar ambiente virtual se não existir
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python -m venv venv
fi

# Ativar ambiente virtual
source venv/bin/activate

# Instalar dependências
echo "Instalando dependências..."
pip install -r requirements.txt

# Inicializar banco de dados
echo "Inicializando banco de dados..."
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Executar aplicação
echo "Iniciando API..."
gunicorn wsgi:app
