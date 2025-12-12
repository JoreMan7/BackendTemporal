from flask import Blueprint, request, jsonify
from database import db
from models import (
    TipoDocumento, Sexo, TipoUsuario, TipoSacramento, EstadoCita, 
    TipoCita, TipoCurso, Parroquia, Sector, ConfigSistema, 
    ConfigValidacion, ConfigSeguridad, ConfigCitas, Permiso
)
from datetime import datetime

parametrizacion_bp = Blueprint('parametrizacion', __name__)

# ==================== ENDPOINTS GENERALES ====================

@parametrizacion_bp.route('/api/parametrizacion/general', methods=['GET'])
def obtener_config_general():
    """Obtiene la configuración general del sistema"""
    try:
        config = ConfigSistema.query.first()
        if not config:
            config = ConfigSistema()
            db.session.add(config)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': config.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/usuarios/tipos-documento/<int:id>', methods=['PUT'])
def editar_tipo_documento(id):
    try:
        data = request.get_json()
        tipo = TipoDocumento.query.get(id)

        if not tipo:
            return jsonify({'success': False, 'error': 'Tipo no encontrado'}), 404

        tipo.Descripcion = data.get('descripcion')  # 👈 AQUÍ EL CAMBIO

        db.session.commit()

        return jsonify({'success': True, 'message': 'Tipo de documento actualizado'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500



# ==================== MÓDULO USUARIOS ====================

@parametrizacion_bp.route('/api/parametrizacion/usuarios/tipos-documento', methods=['GET'])
def obtener_tipos_documento():
    """Obtiene todos los tipos de documento"""
    try:
        tipos = TipoDocumento.query.all()
        return jsonify({
            'success': True,
            'data': [tipo.to_dict() for tipo in tipos]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/usuarios/tipos-documento', methods=['POST'])
def crear_tipo_documento():
    """Crea un nuevo tipo de documento"""
    try:
        data = request.get_json()
        nuevo_tipo = TipoDocumento(Descripcion=data['descripcion'])
        db.session.add(nuevo_tipo)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Tipo de documento creado',
            'data': nuevo_tipo.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/usuarios/tipos-documento/<int:id>', methods=['PUT'])
def actualizar_tipo_documento(id):
    """Actualiza un tipo de documento"""
    try:
        data = request.get_json()
        tipo = TipoDocumento.query.get_or_404(id)
        tipo.Descripcion = data['descripcion']
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Tipo de documento actualizado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/usuarios/tipos-documento/<int:id>', methods=['DELETE'])
def eliminar_tipo_documento(id):
    """Elimina un tipo de documento"""
    try:
        tipo = TipoDocumento.query.get_or_404(id)
        db.session.delete(tipo)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Tipo de documento eliminado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/usuarios/sexos', methods=['GET'])
def obtener_sexos():
    """Obtiene todos los sexos"""
    try:
        sexos = Sexo.query.all()
        return jsonify({
            'success': True,
            'data': [sexo.to_dict() for sexo in sexos]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/usuarios/roles', methods=['GET'])
def obtener_roles():
    """Obtiene todos los roles del sistema"""
    try:
        roles = TipoUsuario.query.all()
        return jsonify({
            'success': True,
            'data': [rol.to_dict() for rol in roles]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        
@parametrizacion_bp.route('/api/parametrizacion/usuarios/roles', methods=['POST'])
def agregar_rol():
    try:
        data = request.json
        nuevo_rol = TipoUsuario(Perfil=data['perfil'], Descripcion="")
        db.session.add(nuevo_rol)
        db.session.commit()
        return jsonify({'success': True, 'data': nuevo_rol.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@parametrizacion_bp.route('/api/parametrizacion/usuarios/validaciones', methods=['GET'])
def obtener_validaciones():
    """Obtiene la configuración de validaciones"""
    try:
        config = ConfigValidacion.query.first()
        if not config:
            config = ConfigValidacion()
            db.session.add(config)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': config.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/usuarios/validaciones', methods=['PUT'])
def actualizar_validaciones():
    """Actualiza la configuración de validaciones"""
    try:
        data = request.get_json()
        config = ConfigValidacion.query.first()
        
        if not config:
            config = ConfigValidacion(**data)
            db.session.add(config)
        else:
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Validaciones actualizadas'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== MÓDULO HABITANTES ====================

@parametrizacion_bp.route('/api/parametrizacion/habitantes/sacramentos', methods=['GET'])
def obtener_sacramentos():
    """Obtiene todos los tipos de sacramento"""
    try:
        sacramentos = TipoSacramento.query.all()
        return jsonify({
            'success': True,
            'data': [sacramento.to_dict() for sacramento in sacramentos]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/habitantes/parroquias', methods=['GET'])
def obtener_parroquias():
    """Obtiene todas las parroquias"""
    try:
        parroquias = Parroquia.query.all()
        return jsonify({
            'success': True,
            'data': [parroquia.to_dict() for parroquia in parroquias]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/habitantes/sectores', methods=['GET'])
def obtener_sectores():
    """Obtiene todos los sectores"""
    try:
        sectores = Sector.query.all()
        return jsonify({
            'success': True,
            'data': [sector.to_dict() for sector in sectores]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== MÓDULO CITAS ====================

@parametrizacion_bp.route('/api/parametrizacion/citas/tipos', methods=['GET'])
def obtener_tipos_cita():
    """Obtiene todos los tipos de cita"""
    try:
        tipos = TipoCita.query.all()
        return jsonify({
            'success': True,
            'data': [tipo.to_dict() for tipo in tipos]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/citas/estados', methods=['GET'])
def obtener_estados_cita():
    """Obtiene todos los estados de cita"""
    try:
        estados = EstadoCita.query.all()
        return jsonify({
            'success': True,
            'data': [estado.to_dict() for estado in estados]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/citas/configuracion', methods=['GET'])
def obtener_config_citas():
    """Obtiene la configuración de citas"""
    try:
        config = ConfigCitas.query.first()
        if not config:
            config = ConfigCitas()
            db.session.add(config)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': config.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/citas/configuracion', methods=['PUT'])
def actualizar_config_citas():
    """Actualiza la configuración de citas"""
    try:
        data = request.get_json()
        config = ConfigCitas.query.first()
        
        if not config:
            config = ConfigCitas(**data)
            db.session.add(config)
        else:
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Configuración de citas actualizada'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== MÓDULO AYUDANTES ====================

@parametrizacion_bp.route('/api/parametrizacion/ayudantes/cursos', methods=['GET'])
def obtener_cursos():
    """Obtiene todos los tipos de curso"""
    try:
        cursos = TipoCurso.query.filter_by(Activo=True).all()
        return jsonify({
            'success': True,
            'data': [curso.to_dict() for curso in cursos]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== MÓDULO SEGURIDAD ====================

@parametrizacion_bp.route('/api/parametrizacion/seguridad/configuracion', methods=['GET'])
def obtener_config_seguridad():
    """Obtiene la configuración de seguridad"""
    try:
        config = ConfigSeguridad.query.first()
        if not config:
            config = ConfigSeguridad()
            db.session.add(config)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': config.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/seguridad/configuracion', methods=['PUT'])
def actualizar_config_seguridad():
    """Actualiza la configuración de seguridad"""
    try:
        data = request.get_json()
        config = ConfigSeguridad.query.first()
        
        if not config:
            config = ConfigSeguridad(**data)
            db.session.add(config)
        else:
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Configuración de seguridad actualizada'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/seguridad/permisos', methods=['GET'])
def obtener_permisos():
    """Obtiene todos los permisos del sistema"""
    try:
        permisos = Permiso.query.all()
        return jsonify({
            'success': True,
            'data': [permiso.to_dict() for permiso in permisos]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ENDPOINT PARA TODOS LOS DATOS ====================

@parametrizacion_bp.route('/api/parametrizacion/todos', methods=['GET'])
def obtener_todos_datos():
    """Obtiene todos los datos de parametrización en un solo endpoint"""
    try:
        # Obtener todos los datos
        data = {
            'general': obtener_config_general().json['data'] if ConfigSistema.query.first() else {},
            'tipos_documento': [t.to_dict() for t in TipoDocumento.query.all()],
            'sexos': [s.to_dict() for s in Sexo.query.all()],
            'roles': [r.to_dict() for r in TipoUsuario.query.all()],
            'validaciones': obtener_validaciones().json['data'] if ConfigValidacion.query.first() else {},
            'sacramentos': [s.to_dict() for s in TipoSacramento.query.all()],
            'parroquias': [p.to_dict() for p in Parroquia.query.all()],
            'sectores': [s.to_dict() for s in Sector.query.all()],
            'tipos_cita': [t.to_dict() for t in TipoCita.query.all()],
            'estados_cita': [e.to_dict() for e in EstadoCita.query.all()],
            'config_citas': obtener_config_citas().json['data'] if ConfigCitas.query.first() else {},
            'cursos': [c.to_dict() for c in TipoCurso.query.filter_by(Activo=True).all()],
            'seguridad': obtener_config_seguridad().json['data'] if ConfigSeguridad.query.first() else {},
            'permisos': [p.to_dict() for p in Permiso.query.all()]
        }
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@parametrizacion_bp.route('/api/parametrizacion/guardar-todos', methods=['POST'])
def guardar_todos_datos():
    """Guarda todos los datos de parametrización"""
    try:
        data = request.get_json()
        
        # Actualizar cada módulo
        if 'general' in data:
            actualizar_config_general(data['general'])
        
        if 'validaciones' in data:
            actualizar_validaciones(data['validaciones'])
        
        if 'config_citas' in data:
            actualizar_config_citas(data['config_citas'])
        
        if 'seguridad' in data:
            actualizar_config_seguridad(data['seguridad'])
        
        return jsonify({
            'success': True,
            'message': 'Todos los datos guardados exitosamente'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500