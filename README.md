# Backend de Gestión Eclesial

Sistema backend desarrollado en Python con Flask para la gestión de una comunidad eclesial.

## Características

- **Autenticación JWT**: Sistema seguro de autenticación con tokens
- **Roles de usuario**: Administrador, Secretario, Encuestador
- **Base de datos MySQL**: Conexión a base de datos existente
- **API RESTful**: Endpoints bien estructurados
- **Logging**: Sistema completo de logs
- **Seguridad**: Validación y sanitización de datos

## Estructura del Proyecto

\`\`\`
├── database/           # Configuración de base de datos
├── models/            # Modelos de datos
├── routes/            # Rutas y endpoints
├── services/          # Lógica de negocio
├── utils/             # Utilidades y helpers
├── tests/             # Pruebas unitarias
├── uploads/           # Archivos subidos
├── app.py             # Aplicación principal
├── config.py          # Configuración
└── requirements.txt   # Dependencias
\`\`\`

## Instalación y Configuración

### 1. Clonar el repositorio
\`\`\`bash
git clone <url-del-repositorio>
cd gestion-eclesial-backend
\`\`\`

### 2. Crear entorno virtual
\`\`\`bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
\`\`\`

### 3. Instalar dependencias
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 4. Configurar base de datos
- Asegúrate de tener MySQL instalado y ejecutándose
- Crea la base de datos usando el script SQL proporcionado
- Configura las credenciales en el archivo `.env`

### 5. Configurar variables de entorno
Copia el archivo `.env.example` a `.env` y configura:
\`\`\`env
MYSQL_HOST=localhost
MYSQL_USER=tu_usuario
MYSQL_PASSWORD=tu_contraseña
MYSQL_DB=Gestion_Eclesial
SECRET_KEY=tu-clave-secreta
JWT_SECRET_KEY=tu-jwt-secret
\`\`\`

### 6. Ejecutar la aplicación
\`\`\`bash
python app.py
\`\`\`

La aplicación estará disponible en `http://localhost:5000`

## Endpoints Principales

### Autenticación
- `POST /api/auth/login` - Iniciar sesión
- `POST /api/auth/register` - Registrar usuario
- `POST /api/auth/refresh` - Refrescar token
- `GET /api/auth/profile` - Obtener perfil
- `PUT /api/auth/profile` - Actualizar perfil

### Datos
- `GET /api/habitantes` - Listar habitantes
- `GET /api/parroquias` - Listar parroquias
- `GET /api/dashboard/stats` - Estadísticas

### Sistema
- `GET /api/` - Información de la API
- `GET /api/health` - Estado del sistema

## Roles de Usuario

1. **Administrador**: Acceso completo al sistema
2. **Secretario**: Gestión de datos y reportes
3. **Encuestador**: Registro y consulta de información

## Seguridad

- Contraseñas hasheadas con PBKDF2
- Tokens JWT con expiración
- Validación de entrada de datos
- Sanitización contra inyecciones
- Logs de seguridad

## Desarrollo

### Ejecutar en modo desarrollo
\`\`\`bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
\`\`\`

### Ejecutar pruebas
\`\`\`bash
python -m pytest tests/
\`\`\`

## Producción

Para desplegar en producción:

1. Configurar `FLASK_ENV=production`
2. Usar un servidor WSGI como Gunicorn
3. Configurar proxy reverso (Nginx)
4. Configurar SSL/HTTPS
5. Configurar backup de base de datos

\`\`\`bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
\`\`\`

## Contribución

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT.
\`\`\`

Finalmente, creemos un archivo de inicialización de tests:

```python file="tests/__init__.py"
"""
Inicialización del módulo de tests
"""
