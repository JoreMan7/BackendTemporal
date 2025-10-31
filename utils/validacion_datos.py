# validacion_datos.py
from database import execute_query
from datetime import datetime

class ValidacionDatos:
    
    # Esquemas de validación por tabla
    ESQUEMAS_VALIDACION = {
        'habitantes': {
            'campos_obligatorios': [
                'Nombre', 'Apellido', 'IdTipoDocumento', 'NumeroDocumento',
                'FechaNacimiento', 'IdTipoPoblacion', 'Direccion', 'Telefono',
                'CorreoElectronico', 'IdGrupoFamiliar', 'IdSexo', 'IdEstadoCivil',
                'IdReligion', 'IdSector'
            ],
            'esquema_tipos': {
                'Nombre': 'texto',
                'Apellido': 'texto',
                'IdTipoDocumento': 'entero',
                'NumeroDocumento': 'texto',
                'FechaNacimiento': 'fecha',
                'Hijos': 'entero',
                'DiscapacidadParaAsistir': 'texto',
                'IdTipoPoblacion': 'entero',
                'Direccion': 'texto',
                'Telefono': 'texto',
                'CorreoElectronico': 'email',
                'IdGrupoFamiliar': 'entero',
                'TieneImpedimentoSalud': 'booleano',
                'MotivoImpedimentoSalud': 'texto',
                'IdSexo': 'entero',
                'IdEstadoCivil': 'entero',
                'IdReligion': 'entero',
                'IdSector': 'entero'
            },
            'campos_unicos': ['CorreoElectronico', 'NumeroDocumento']
        },
        'habitante_sacramento': {
            'campos_obligatorios': ['IdHabitante', 'IdSacramento'],
            'esquema_tipos': {
                'IdHabitante': 'entero',
                'IdSacramento': 'entero',
                'FechaSacramento': 'fecha'
            },
            'campos_unicos': []  # La primary key compuesta ya maneja la unicidad
        }
        # Puedes agregar más tablas aquí según necesites
    }
    
    @staticmethod
    def validar_vacios(data, tabla):
        """
        Valida campos vacíos u omitidos para una tabla específica
        """
        if tabla not in ValidacionDatos.ESQUEMAS_VALIDACION:
            return {'valido': True, 'mensaje': 'Tabla sin esquema de validación'}
        
        campos_obligatorios = ValidacionDatos.ESQUEMAS_VALIDACION[tabla]['campos_obligatorios']
        campos_faltantes = []
        
        for campo in campos_obligatorios:
            valor = data.get(campo)
            if valor is None or valor == '':
                campos_faltantes.append(campo)
        
        if campos_faltantes:
            return {
                'valido': False,
                'mensaje': f'Faltan campos obligatorios: {", ".join(campos_faltantes)}',
                'campos_faltantes': campos_faltantes
            }
        
        return {'valido': True, 'mensaje': 'Todos los campos obligatorios están presentes'}
    
    @staticmethod
    def validar_tipos_datos(data, tabla):
        """
        Valida tipos de datos para una tabla específica
        """
        if tabla not in ValidacionDatos.ESQUEMAS_VALIDACION:
            return {'valido': True, 'mensaje': 'Tabla sin esquema de validación'}
        
        esquema_tipos = ValidacionDatos.ESQUEMAS_VALIDACION[tabla]['esquema_tipos']
        errores_tipo = []
        
        for campo, tipo_esperado in esquema_tipos.items():
            valor = data.get(campo)
            
            if valor is None or valor == '':
                continue  # Los vacíos ya se validan en validar_vacios
                
            if tipo_esperado == 'entero':
                try:
                    int(valor)
                except (ValueError, TypeError):
                    errores_tipo.append(f'"{campo}" debe ser un número entero')
                    
            elif tipo_esperado == 'decimal':
                try:
                    float(valor)
                except (ValueError, TypeError):
                    errores_tipo.append(f'"{campo}" debe ser un número decimal')
                    
            elif tipo_esperado == 'fecha':
                if not isinstance(valor, str):
                    errores_tipo.append(f'"{campo}" debe ser una fecha en formato texto')
                else:
                    try:
                        datetime.strptime(valor, '%Y-%m-%d')
                    except ValueError:
                        errores_tipo.append(f'"{campo}" debe tener formato YYYY-MM-DD')
                    
            elif tipo_esperado == 'email':
                if not isinstance(valor, str) or '@' not in valor or '.' not in valor:
                    errores_tipo.append(f'"{campo}" debe ser un correo electrónico válido')
                    
            elif tipo_esperado == 'texto':
                if not isinstance(valor, str):
                    errores_tipo.append(f'"{campo}" debe ser texto')
                    
            elif tipo_esperado == 'booleano':
                if valor not in [0, 1, True, False, '0', '1', 'true', 'false']:
                    errores_tipo.append(f'"{campo}" debe ser verdadero o falso')
        
        if errores_tipo:
            return {
                'valido': False,
                'mensaje': 'Errores en tipos de datos: ' + '; '.join(errores_tipo),
                'errores_tipo': errores_tipo
            }
        
        return {'valido': True, 'mensaje': 'Tipos de datos correctos'}
    
    @staticmethod
    def validar_repetidos(data, tabla, registro_id=None):
        """
        Valida campos únicos para evitar duplicados
        """
        if tabla not in ValidacionDatos.ESQUEMAS_VALIDACION:
            return {'valido': True, 'mensaje': 'Tabla sin esquema de validación'}
        
        campos_unicos = ValidacionDatos.ESQUEMAS_VALIDACION[tabla]['campos_unicos']
        campos_repetidos = []
        
        for campo in campos_unicos:
            valor = data.get(campo)
            if valor is None or valor == '':
                continue
                
            # Construir query para verificar duplicados
            query = f"SELECT 1 FROM {tabla} WHERE {campo} = %s AND Activo = 1"
            params = [valor]
            
            # Si es una actualización, excluir el registro actual
            if registro_id is not None:
                query += " AND IdHabitante != %s"
                params.append(registro_id)
            
            existente = execute_query(query, tuple(params), fetch_one=True)
            if existente:
                campos_repetidos.append(campo)
        
        if campos_repetidos:
            return {
                'valido': False,
                'mensaje': f'Ya existen registros con estos datos: {", ".join(campos_repetidos)}',
                'campos_repetidos': campos_repetidos
            }
        
        return {'valido': True, 'mensaje': 'No hay duplicados en campos únicos'}
    
    @staticmethod
    def validar_completo(data, tabla, registro_id=None):
        """
        Validación completa: vacíos, tipos y duplicados
        """
        resultados = []
        
        # Validar vacíos
        resultado_vacios = ValidacionDatos.validar_vacios(data, tabla)
        resultados.append(resultado_vacios)
        if not resultado_vacios['valido']:
            return resultado_vacios
        
        # Validar tipos de datos
        resultado_tipos = ValidacionDatos.validar_tipos_datos(data, tabla)
        resultados.append(resultado_tipos)
        if not resultado_tipos['valido']:
            return resultado_tipos
        
        # Validar duplicados (solo para habitantes por ahora)
        if tabla == 'habitantes':
            resultado_duplicados = ValidacionDatos.validar_repetidos(data, tabla, registro_id)
            resultados.append(resultado_duplicados)
            if not resultado_duplicados['valido']:
                return resultado_duplicados
        
        return {
            'valido': True,
            'mensaje': 'Todas las validaciones pasaron correctamente',
            'resultados': resultados
        }