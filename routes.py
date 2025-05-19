import os
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from models import db, User, Report, ReportImage
from auth import token_required, admin_required, generate_token
from datetime import datetime
import uuid

api = Blueprint('api', __name__)

# Funções auxiliares
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rotas de autenticação
@api.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Verifica se todos os campos necessários estão presentes
    if not all(k in data for k in ('name', 'email', 'password')):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Verifica se o email já está em uso
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already registered'}), 409
    
    # Cria um novo usuário
    new_user = User(
        name=data['name'],
        email=data['email'],
        role=data.get('role', 'user')  # Default é 'user'
    )
    new_user.set_password(data['password'])
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), 201

@api.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not all(k in data for k in ('email', 'password')):
        return jsonify({'message': 'Missing email or password'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Invalid email or password'}), 401
    
    token = generate_token(user.id, user.role)
    
    return jsonify({
        'token': token,
        'user': user.to_dict()
    }), 200

# Rotas de usuários
@api.route('/users', methods=['GET'])
@admin_required
def get_users(current_user_id):
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

@api.route('/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(current_user_id, user_id):
    # Apenas admins podem ver outros usuários
    if int(current_user_id) != user_id:
        user = User.query.get(current_user_id)
        if user.role != 'admin':
            return jsonify({'message': 'Unauthorized'}), 403
    
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200

@api.route('/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(current_user_id, user_id):
    # Apenas o próprio usuário ou um admin pode atualizar
    if int(current_user_id) != user_id:
        user = User.query.get(current_user_id)
        if user.role != 'admin':
            return jsonify({'message': 'Unauthorized'}), 403
    
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        # Verifica se o email já está em uso por outro usuário
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'message': 'Email already in use'}), 409
        user.email = data['email']
    if 'password' in data:
        user.set_password(data['password'])
    if 'role' in data:
        # Apenas admins podem mudar roles
        current_user = User.query.get(current_user_id)
        if current_user.role == 'admin':
            user.role = data['role']
    
    db.session.commit()
    return jsonify(user.to_dict()), 200

@api.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_user_id, user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200

# Rotas de denúncias
@api.route('/reports', methods=['GET'])
@token_required
def get_reports(current_user_id):
    user = User.query.get(current_user_id)
    
    # Filtros
    status = request.args.get('status')
    type = request.args.get('type')
    
    query = Report.query
    
    # Usuários normais só veem suas próprias denúncias
    if user.role != 'admin':
        query = query.filter_by(user_id=current_user_id)
    
    # Aplicar filtros se fornecidos
    if status:
        query = query.filter_by(status=status)
    if type:
        query = query.filter_by(type=type)
    
    reports = query.order_by(Report.created_at.desc()).all()
    return jsonify([report.to_dict() for report in reports]), 200

@api.route('/reports/<int:report_id>', methods=['GET'])
@token_required
def get_report(current_user_id, report_id):
    report = Report.query.get_or_404(report_id)
    user = User.query.get(current_user_id)
    
    # Verificar permissão
    if user.role != 'admin' and report.user_id != int(current_user_id):
        return jsonify({'message': 'Unauthorized'}), 403
    
    return jsonify(report.to_dict()), 200

@api.route('/reports', methods=['POST'])
@token_required
def create_report(current_user_id):
    data = request.get_json()
    
    # Verificar campos obrigatórios
    if not all(k in data for k in ('title', 'description', 'type')):
        return jsonify({'message': 'Missing required fields'}), 400
    
    new_report = Report(
        title=data['title'],
        description=data['description'],
        type=data['type'],
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        address=data.get('address'),
        user_id=current_user_id
    )
    
    db.session.add(new_report)
    db.session.commit()
    
    return jsonify(new_report.to_dict()), 201

@api.route('/reports/<int:report_id>', methods=['PUT'])
@token_required
def update_report(current_user_id, report_id):
    report = Report.query.get_or_404(report_id)
    user = User.query.get(current_user_id)
    
    # Verificar permissão
    if user.role != 'admin' and report.user_id != int(current_user_id):
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    # Usuários normais só podem atualizar alguns campos
    if user.role != 'admin':
        allowed_fields = ['title', 'description', 'type', 'latitude', 'longitude', 'address']
        for field in allowed_fields:
            if field in data:
                setattr(report, field, data[field])
    else:
        # Admins podem atualizar todos os campos
        for field in data:
            if hasattr(report, field):
                setattr(report, field, data[field])
    
    report.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(report.to_dict()), 200

@api.route('/reports/<int:report_id>', methods=['DELETE'])
@token_required
def delete_report(current_user_id, report_id):
    report = Report.query.get_or_404(report_id)
    user = User.query.get(current_user_id)
    
    # Verificar permissão
    if user.role != 'admin' and report.user_id != int(current_user_id):
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Excluir imagens associadas do sistema de arquivos
    for image in report.images:
        try:
            os.remove(image.file_path)
        except:
            pass  # Ignora erros ao excluir arquivos
    
    db.session.delete(report)
    db.session.commit()
    
    return jsonify({'message': 'Report deleted successfully'}), 200

# Rotas para imagens de denúncias
@api.route('/reports/<int:report_id>/images', methods=['POST'])
@token_required
def upload_image(current_user_id, report_id):
    report = Report.query.get_or_404(report_id)
    user = User.query.get(current_user_id)
    
    # Verificar permissão
    if user.role != 'admin' and report.user_id != int(current_user_id):
        return jsonify({'message': 'Unauthorized'}), 403
    
    if 'image' not in request.files:
        return jsonify({'message': 'No image part'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        # Criar diretório de uploads se não existir
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        # Gerar nome de arquivo único
        filename = secure_filename(file.filename) 
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(upload_folder, unique_filename)
        
        # Salvar arquivo
        file.save(file_path)
         
        # Criar registro no banco de dados
        new_image = ReportImage(
            filename=unique_filename,
            file_path=file_path,
            report_id=report_id
        )
        
        db.session.add(new_image)
        db.session.commit()
        
        return jsonify(new_image.to_dict()), 201
    
    return jsonify({'message': 'File type not allowed'}), 400

@api.route('/images/<int:image_id>', methods=['GET'])
def get_image(image_id):
    image = ReportImage.query.get_or_404(image_id)
    return send_from_directory(
        os.path.dirname(image.file_path),
        os.path.basename(image.file_path)
    )

@api.route('/images/<int:image_id>', methods=['DELETE'])
@token_required
def delete_image(current_user_id, image_id):
    image = ReportImage.query.get_or_404(image_id)
    report = Report.query.get(image.report_id)
    user = User.query.get(current_user_id)
    
    # Verificar permissão
    if user.role != 'admin' and report.user_id != int(current_user_id):
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Excluir arquivo
    try:
        os.remove(image.file_path)
    except:
        pass  # Ignora erros ao excluir arquivo
    
    db.session.delete(image)
    db.session.commit()
    
    return jsonify({'message': 'Image deleted successfully'}), 200

# Rotas para estatísticas (apenas admin)
@api.route('/statistics', methods=['GET'])
@admin_required
def get_statistics(current_user_id):
    # Total de denúncias
    total_reports = Report.query.count()
    
    # Denúncias por status
    pending_count = Report.query.filter_by(status='pending').count()
    investigating_count = Report.query.filter_by(status='investigating').count()
    resolved_count = Report.query.filter_by(status='resolved').count()
    rejected_count = Report.query.filter_by(status='rejected').count()
    
    # Denúncias por tipo
    report_types = db.session.query(
        Report.type, 
        db.func.count(Report.id)
    ).group_by(Report.type).all()
    
    types_data = {type_name: count for type_name, count in report_types}
    
    # Denúncias por mês (últimos 6 meses)
    six_months_ago = datetime.utcnow().replace(day=1)
    for i in range(5):
        six_months_ago = six_months_ago.replace(month=six_months_ago.month-1 if six_months_ago.month > 1 else 12)
        if six_months_ago.month == 12:
            six_months_ago = six_months_ago.replace(year=six_months_ago.year-1)
    
    monthly_reports = db.session.query(
        db.func.extract('year', Report.created_at).label('year'),
        db.func.extract('month', Report.created_at).label('month'),
        db.func.count(Report.id).label('count')
    ).filter(Report.created_at >= six_months_ago).group_by('year', 'month').all()
    
    monthly_data = [
        {
            'year': int(year),
            'month': int(month),
            'count': count
        } for year, month, count in monthly_reports
    ]
    
    return jsonify({
        'total_reports': total_reports,
        'by_status': {
            'pending': pending_count,
            'investigating': investigating_count,
            'resolved': resolved_count,
            'rejected': rejected_count
        },
        'by_type': types_data,
        'monthly_data': monthly_data
    }), 200
