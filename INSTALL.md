# Instalación y Configuración - Design Tools

## Requisitos Previos

### Para el Backend (FastAPI)
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Para el Frontend (React)
- Node.js 16 o superior
- npm 8 o superior

## Instalación Paso a Paso

### 1. Clonar o Crear la Estructura

Si ya tienes la estructura del proyecto en `C:\Users\ROG1\Design Tools`, puedes continuar con los siguientes pasos.

### 2. Configurar el Backend (FastAPI)

1. **Abrir terminal en la carpeta backend:**
   ```bash
   cd "C:\Users\ROG1\Design Tools\backend"
   ```

2. **Crear entorno virtual:**
   ```bash
   python -m venv venv
   ```

3. **Activar entorno virtual:**
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD):**
     ```cmd
     venv\Scripts\activate.bat
     ```
   - **Linux/Mac:**
     ```bash
     source venv/bin/activate
     ```

4. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Verificar instalación:**
   ```bash
   python -c "import fastapi; print(f'FastAPI version: {fastapi.__version__}')"
   ```

### 3. Configurar el Frontend (React)

1. **Abrir terminal en la carpeta frontend:**
   ```bash
   cd "C:\Users\ROG1\Design Tools\frontend"
   ```

2. **Instalar dependencias:**
   ```bash
   npm install
   ```

   Esto instalará:
   - React y React DOM
   - Material-UI y iconos
   - React Router DOM
   - Axios para peticiones HTTP
   - React Hook Form y Zod para validación
   - Framer Motion para animaciones
   - React Hot Toast para notificaciones

3. **Verificar instalación:**
   ```bash
   npm list react
   ```

## Ejecución del Proyecto

### Opción 1: Ejecutar por Separado

#### Backend:
```bash
cd "C:\Users\ROG1\Design Tools\backend"
.\venv\Scripts\Activate.ps1  # Solo en Windows PowerShell
python main.py
```

El backend estará disponible en: **http://localhost:8000**
- API: http://localhost:8000
- Documentación: http://localhost:8000/docs
- Health check: http://localhost:8000/health

#### Frontend:
```bash
cd "C:\Users\ROG1\Design Tools\frontend"
npm start
```

El frontend estará disponible en: **http://localhost:3000**

### Opción 2: Script de Ejecución Simultánea (Windows)

Crea un archivo `run.bat` en la raíz del proyecto:

```batch
@echo off
echo Iniciando Design Tools...

REM Iniciar backend
start "Backend" cmd /k "cd /d "C:\Users\ROG1\Design Tools\backend" && call venv\Scripts\activate.bat && python main.py"

REM Esperar 3 segundos para que el backend inicie
timeout /t 3 /nobreak > nul

REM Iniciar frontend
start "Frontend" cmd /k "cd /d "C:\Users\ROG1\Design Tools\frontend" && npm start"

echo.
echo Aplicaciones iniciadas:
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:3000
echo.
pause
```

## Configuración Adicional

### Variables de Entorno del Backend

El archivo `backend/.env` ya está configurado con valores por defecto. Para producción, cambia:

1. **SECRET_KEY**: Genera una clave segura:
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```

2. **DATABASE_URL**: Para producción, usa PostgreSQL o MySQL:
   ```
   DATABASE_URL=postgresql://usuario:contraseña@localhost/design_tools
   ```

### Configuración del Proxy en Frontend

El `package.json` del frontend ya tiene configurado:
```json
"proxy": "http://localhost:8000"
```

Esto permite que las peticiones del frontend al backend funcionen sin problemas de CORS durante el desarrollo.

## Solución de Problemas

### Problema: Backend no inicia
- **Solución:** Verifica que Python esté instalado:
  ```bash
  python --version
  ```
- **Solución:** Verifica las dependencias:
  ```bash
  pip list
  ```

### Problema: Frontend no inicia
- **Solución:** Verifica Node.js:
  ```bash
  node --version
  npm --version
  ```
- **Solución:** Limpia cache de npm:
  ```bash
  npm cache clean --force
  rm -rf node_modules package-lock.json
  npm install
  ```

### Problema: CORS errors
- **Solución:** Verifica que el backend esté corriendo en el puerto 8000
- **Solución:** Verifica la configuración de CORS en `backend/main.py`

### Problema: Imágenes no se cargan
- **Solución:** Las imágenes usan URLs públicas de Google. Si hay problemas de carga, puedes reemplazarlas con imágenes locales.

## Estructura de Archivos Completada

Tu proyecto ahora tiene:

```
C:\Users\ROG1\Design Tools\
├── frontend\
│   ├── public\
│   │   └── index.html
│   ├── src\
│   │   ├── components\
│   │   │   └── Layout.js
│   │   ├── pages\
│   │   │   ├── Dashboard.js
│   │   │   ├── Login.js
│   │   │   ├── Register.js
│   │   │   └── DesignStudio.js
│   │   ├── App.js
│   │   ├── index.js
│   │   └── index.css
│   └── package.json
├── backend\
│   ├── main.py
│   ├── requirements.txt
│   ├── .env
│   └── .gitignore
├── README.md
└── INSTALL.md
```

## Primeros Pasos

1. **Inicia el backend:** Sigue las instrucciones en la sección "Ejecución del Proyecto"
2. **Inicia el frontend:** En otra terminal, inicia el servidor de React
3. **Accede a la aplicación:** Abre http://localhost:3000 en tu navegador
4. **Regístrate o inicia sesión:** Usa el formulario de registro/login
5. **Explora el dashboard:** Verás proyectos de ejemplo y herramientas
6. **Prueba el editor:** Haz clic en "Abrir Editor" en cualquier proyecto

## Desarrollo Adicional

Para continuar desarrollando:

1. **Agregar más páginas:** Crea nuevos archivos en `frontend/src/pages/`
2. **Extender la API:** Agrega nuevos endpoints en `backend/main.py`
3. **Conectar base de datos:** Configura SQLAlchemy con modelos
4. **Agregar autenticación real:** Implementa JWT y protección de rutas
5. **Mejorar el editor:** Agrega más herramientas de diseño

## Soporte

Si encuentras problemas:

1. Revisa los mensajes de error en la terminal
2. Verifica que todos los servicios estén corriendo
3. Asegúrate de tener las versiones correctas de Python y Node.js
4. Revisa la configuración de puertos (8000 para backend, 3000 para frontend)

¡Tu proyecto Design Tools está listo para usar! 🚀