"""
Utilidades de seguridad para el manejo de contraseñas y tokens
"""
import hashlib
import secrets
import re
from werkzeug.security import generate_password_hash, check_password_hash

class Security:
    """Clase para manejo de seguridad"""
    
    @staticmethod
    def generate_password_hash(password):
        """
        Genera un hash seguro de la contraseña
        
        Args:
            password (str): Contraseña en texto plano
            
        Returns:
            str: Hash de la contraseña
        """
        return generate_password_hash(password, method='pbkdf2:sha256')
    
    @staticmethod
    def check_password_hash(password_hash, password):
        """
        Verifica si una contraseña coincide con su hash
        
        Args:
            password_hash (str): Hash almacenado
            password (str): Contraseña a verificar
            
        Returns:
            bool: True si coincide, False en caso contrario
        """
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def validate_password(password):
        """
        Valida que una contraseña cumpla con los requisitos de seguridad
        
        Args:
            password (str): Contraseña a validar
            
        Returns:
            dict: Resultado de la validación
        """
        errors = []
        
        if len(password) < 8:
            errors.append("La contraseña debe tener al menos 8 caracteres")
        
        if not re.search(r"[A-Z]", password):
            errors.append("La contraseña debe contener al menos una letra mayúscula")
        
        if not re.search(r"[a-z]", password):
            errors.append("La contraseña debe contener al menos una letra minúscula")
        
        if not re.search(r"\d", password):
            errors.append("La contraseña debe contener al menos un número")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("La contraseña debe contener al menos un carácter especial")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def validate_email(email):
        """
        Valida formato de email
        
        Args:
            email (str): Email a validar
            
        Returns:
            bool: True si es válido, False en caso contrario
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def generate_token():
        """
        Genera un token aleatorio seguro
        
        Returns:
            str: Token generado
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def sanitize_input(input_string):
        """
        Sanitiza entrada de usuario para prevenir inyecciones
        
        Args:
            input_string (str): Cadena a sanitizar
            
        Returns:
            str: Cadena sanitizada
        """
        if not isinstance(input_string, str):
            return str(input_string)
        
        # Remover caracteres peligrosos
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`']
        sanitized = input_string
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized.strip()
