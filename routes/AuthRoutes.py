"""
Rutas de autenticación y autorización
Maneja login, registro, refresh de tokens y gestión de usuarios
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, get_jwt,
    create_access_token, create_refresh_token
)
from datetime import datetime, timezone, timedelta
from services import AuthService
from models import UserModel
from utils import Security
import logging
from config import Config
from database import execute_query

from flask import request



# Crear blueprint para autenticación
auth_bp = Blueprint('auth', __name__)

# --- LOGIN ---
@auth_bp.post('/login')
def login():
    try:
        data = request.get_json(silent=True) or {}
        doc_type = data.get('document_type')
        doc_num = data.get('document_number')
        password = data.get('password')

        if not doc_type or not doc_num or not password:
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

        # ⬇️ DELEGAR TODA LA LÓGICA AL SERVICIO
        result = AuthService.login_by_document(doc_type, doc_num, password)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            # El servicio ya maneja los errores (bloqueos, credenciales, etc.)
            status_code = 401
            if result.get('locked'):
                status_code = 423
            return jsonify(result), status_code

    except Exception as e:
        logging.error(f"Error crítico en login: {str(e)}", exc_info=True)
        return jsonify({
            "success": False, 
            "message": "Error interno del servidor"
        }), 500

def calculate_lock_duration(lock_count):
    """
    Calcula la duración del bloqueo usando multiplicador progresivo
    lock_count = 0 (primer bloqueo), 1 (segundo bloqueo), etc.
    """
    base_minutes = Config.BASE_LOCK_DURATION_MINUTES
    multiplier = Config.LOCK_MULTIPLIER
    max_minutes = Config.MAX_LOCK_DURATION_MINUTES
    
    # Fórmula: base * (multiplicador ^ lock_count)
    duration = base_minutes * (multiplier ** lock_count)
    
    # No exceder el máximo
    return min(int(duration), max_minutes)

@auth_bp.get('/verify')
@jwt_required()
def verify_token():
    return jsonify({
        "success": True,
        "user_id": get_jwt_identity(),
        "claims": get_jwt()
    }), 200

@auth_bp.get('/verify-echo')  # <- diagnóstico
def verify_echo():
    auth_header = request.headers.get("Authorization")
    return jsonify({
        "received_authorization": auth_header or None
    }), 200


@auth_bp.post('/refresh')
@jwt_required(refresh=True)
def refresh_token():
    user_id = get_jwt_identity()
    new_access = create_access_token(identity=user_id)
    return jsonify({"success": True, "access_token": new_access}), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Endpoint para registro de nuevos usuarios
    
    Body JSON:
    {
        "nombre": "Juan",
        "apellido": "Pérez",
        "id_tipo_documento": "1",
        "numero_documento": "12345678",
        "password": "MiContraseña123!",
        "correo_electronico": "juan@email.com",
        "telefono": "3001234567"
    }
    
    Returns:
        JSON: Resultado del registro
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Datos requeridos'
            }), 400
        
        # Validar email si se proporciona
        email = data.get('correo_electronico')
        if email and not Security.validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Formato de email inválido'
            }), 400
        
        # Validar contraseña
        password = data.get('password')
        if password:
            password_validation = Security.validate_password(password)
            if not password_validation['valid']:
                return jsonify({
                    'success': False,
                    'message': 'Contraseña no cumple con los requisitos',
                    'errors': password_validation['errors']
                }), 400
        
        # Validar número de documento
        document_number = str(data.get('numero_documento', '')).strip()
        if document_number and not document_number.isdigit():
            return jsonify({
                'success': False,
                'message': 'El número de documento debe contener solo números'
            }), 400
        
        # Actualizar el número de documento limpio
        data['numero_documento'] = document_number
        
        # Registrar usuario
        result = AuthService.register(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logging.error(f"Error en endpoint register: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Endpoint para obtener perfil COMPLETO del usuario actual
    Incluye datos del habitante con todos los JOINs necesarios
    """
    try:
        current_user_id = get_jwt_identity()
        
        query = """
            SELECT 
                u.IdUsuario,
                u.IdTipoUsuario,
                u.FechaRegistro AS FechaRegistroUsuario,
                tu.Perfil AS RolNombre,
                h.IdHabitante,
                h.Nombre,
                h.Apellido,
                h.IdTipoDocumento,
                td.Descripcion AS TipoDocumentoNombre,
                h.NumeroDocumento,
                h.FechaNacimiento,
                h.IdSexo,
                s.Nombre AS SexoNombre,
                h.IdEstadoCivil,
                ec.Nombre AS EstadoCivilNombre,
                h.IdReligion,
                r.Nombre AS ReligionNombre,
                h.IdTipoPoblacion,
                tp.Nombre AS TipoPoblacionNombre,
                h.IdSector,
                sec.Descripcion AS SectorNombre,
                h.IdGrupoFamiliar,
                gf.NombreGrupo AS GrupoFamiliarNombre,
                h.Hijos,
                h.TieneImpedimentoSalud,
                h.MotivoImpedimentoSalud,
                h.Direccion,
                h.Telefono,
                h.CorreoElectronico,
                u.Activo
            FROM usuario u
            LEFT JOIN tipousuario tu ON u.IdTipoUsuario = tu.IdTipoUsuario
            LEFT JOIN habitantes h ON u.IdHabitante = h.IdHabitante
            LEFT JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
            LEFT JOIN sexos s ON h.IdSexo = s.IdSexo
            LEFT JOIN estados_civiles ec ON h.IdEstadoCivil = ec.IdEstadoCivil
            LEFT JOIN religiones r ON h.IdReligion = r.IdReligion
            LEFT JOIN tipopoblacion tp ON h.IdTipoPoblacion = tp.IdTipoPoblacion
            LEFT JOIN sector sec ON h.IdSector = sec.IdSector
            LEFT JOIN grupofamiliar gf ON h.IdGrupoFamiliar = gf.IdGrupoFamiliar
            WHERE u.IdUsuario = %s AND u.Activo = 1
        """
        
        user = execute_query(query, (current_user_id,), fetch_one=True)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        
        user_data = {
            'IdUsuario': user['IdUsuario'],
            'IdHabitante': user['IdHabitante'],
            'Nombre': user['Nombre'],
            'Apellido': user['Apellido'],
            'UserName': f"{user['Nombre']} {user['Apellido']}".strip(),
            'NumeroDocumento': user['NumeroDocumento'],
            'IdTipoDocumento': user['IdTipoDocumento'],
            'TipoDocumentoNombre': user.get('TipoDocumentoNombre'),
            'FechaNacimiento': str(user.get('FechaNacimiento')) if user.get('FechaNacimiento') else None,
            'IdSexo': user.get('IdSexo'),
            'SexoNombre': user.get('SexoNombre'),
            'IdEstadoCivil': user.get('IdEstadoCivil'),
            'EstadoCivilNombre': user.get('EstadoCivilNombre'),
            'IdReligion': user.get('IdReligion'),
            'ReligionNombre': user.get('ReligionNombre'),
            'IdTipoPoblacion': user.get('IdTipoPoblacion'),
            'TipoPoblacionNombre': user.get('TipoPoblacionNombre'),
            'IdSector': user.get('IdSector'),
            'SectorNombre': user.get('SectorNombre'),
            'IdGrupoFamiliar': user.get('IdGrupoFamiliar'),
            'GrupoFamiliarNombre': user.get('GrupoFamiliarNombre'),
            'Hijos': user.get('Hijos', 0),
            'TieneImpedimentoSalud': user.get('TieneImpedimentoSalud', 0),
            'MotivoImpedimentoSalud': user.get('MotivoImpedimentoSalud'),
            'Direccion': user.get('Direccion'),
            'Telefono': user.get('Telefono'),
            'CorreoElectronico': user.get('CorreoElectronico'),
            'RolNombre': user.get('RolNombre', 'Usuario'),
            'IdTipoUsuario': user.get('IdTipoUsuario'),
            'FechaRegistroUsuario': str(user.get('FechaRegistroUsuario')) if user.get('FechaRegistroUsuario') else None,
            'Activo': user.get('Activo', 1)
        }
        
        return jsonify({
            'success': True,
            'user': user_data
        }), 200
        
    except Exception as e:
        logging.error(f"Error en endpoint profile: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500


@auth_bp.route('/document-types', methods=['GET'])
def get_document_types():
    """
    Endpoint para obtener los tipos de documento disponibles
    
    Returns:
        JSON: Lista de tipos de documento
    """
    try:
        result = AuthService.get_document_types()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logging.error(f"Error en endpoint document-types: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor',
            'document_types': []
        }), 500

@auth_bp.route('/security-settings', methods=['GET'])
def get_security_settings():
    """Endpoint para ver la configuración de seguridad (solo admin)"""
    return jsonify({
        "max_login_attempts": Config.MAX_LOGIN_ATTEMPTS,
        "base_lock_duration_minutes": Config.BASE_LOCK_DURATION_MINUTES,
        "lock_multiplier": Config.LOCK_MULTIPLIER,
        "max_lock_duration_minutes": Config.MAX_LOCK_DURATION_MINUTES,
        "lock_examples": {
            "first_lock": calculate_lock_duration(0),
            "second_lock": calculate_lock_duration(1),
            "third_lock": calculate_lock_duration(2),
            "max_lock": Config.MAX_LOCK_DURATION_MINUTES
        }
    })

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Endpoint para cerrar sesión
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        JSON: Confirmación de logout
    """
    try:
        
        return jsonify({
            'success': True,
            'message': 'Sesión cerrada exitosamente'
        }), 200
        
    except Exception as e:
        logging.error(f"Error en endpoint logout: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500

@auth_bp.route('/profile', methods=['PATCH'])
@jwt_required()
def update_profile():
    """
    Actualiza el perfil del usuario autenticado.
    Campos soportados (habitantes): 
      Nombre, Apellido, Telefono, CorreoElectronico, Direccion, 
      IdTipoDocumento, NumeroDocumento, FechaNacimiento (opcional)
    """
    try:
        current_user_id = get_jwt_identity()
        user = UserModel.get_user_by_id(current_user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404

        data = request.get_json() or {}

        # Construir UPDATE dinámico solo con campos presentes
        allowed = {
            'Nombre': 'Nombre',
            'Apellido': 'Apellido',
            'Telefono': 'Telefono',
            'CorreoElectronico': 'CorreoElectronico',
            'Direccion': 'Direccion',
            'IdTipoDocumento': 'IdTipoDocumento',
            'NumeroDocumento': 'NumeroDocumento',
            'FechaNacimiento': 'FechaNacimiento'
        }

        set_parts = []
        params = []
        for k, col in allowed.items():
            if k in data and data[k] not in (None, ''):
                set_parts.append(f"{col} = %s")
                params.append(data[k])

        if not set_parts:
            return jsonify({'success': False, 'message': 'Nada para actualizar'}), 400

        # Donde editar: habitantes (no en usuario)
        # user['IdHabitante'] viene de UserModel.get_user_by_id(...)
        params.append(user['IdHabitante'])
        query = f"UPDATE habitantes SET {', '.join(set_parts)} WHERE IdHabitante = %s"

        updated = execute_query(query, tuple(params))
        if updated is None:
            return jsonify({'success': False, 'message': 'No se pudo actualizar'}), 500

        # Devolver perfil fresco
        refreshed = UserModel.get_user_by_id(current_user_id)
        user_data = {
            'id': refreshed['IdUsuario'],
            'nombre': refreshed['Nombre'],
            'apellido': refreshed['Apellido'],
            'email': refreshed.get('CorreoElectronico'),
            'telefono': refreshed.get('Telefono'),
            'documento': refreshed['NumeroDocumento'],
            'tipo_documento': refreshed.get('IdTipoDocumento'),
            'tipo_documento_nombre': refreshed.get('tipo_documento_nombre'),
            'rol': refreshed.get('rol', 'Usuario'),
            'direccion': refreshed.get('Direccion')
        }

        return jsonify({'success': True, 'user': user_data}), 200

    except Exception as e:
        logging.error(f"Error en update_profile: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500


