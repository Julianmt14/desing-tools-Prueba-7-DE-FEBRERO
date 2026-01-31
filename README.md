# Design Tools - Proyecto de Diseño Estructural

## Descripción

Proyecto completo con frontend React y backend FastAPI para herramientas de diseño estructural y planos arquitectónicos.

## Estructura del Proyecto

```
Design Tools/
├── frontend/           # Aplicación React
│   ├── public/
│   ├── src/
│   │   ├── components/ # Componentes reutilizables
│   │   ├── pages/      # Páginas principales
│   │   ├── App.js      # Componente principal
│   │   └── index.js    # Punto de entrada
│   └── package.json    # Dependencias de React
├── backend/            # API FastAPI
│   ├── main.py         # Aplicación principal
│   ├── requirements.txt # Dependencias de Python
│   ├── .env            # Variables de entorno
│   └── .gitignore      # Archivos ignorados
└── README.md           # Este archivo
```

## Características

### Frontend (React)
- Dashboard con diseño moderno y responsivo
- Sistema de autenticación (login/registro)
- Navegación con barra inferior fija
- Vista de proyectos recientes con imágenes
- Herramientas directas de diseño estructural
- Búsqueda integrada
- Tema oscuro/claro

### Backend (FastAPI)
- API RESTful completa
- Autenticación con JWT
- Modelos Pydantic para validación
- CORS configurado para frontend
- Documentación automática con Swagger UI
- Base de datos SQLite (para desarrollo)

## Instalación y Configuración

### Backend

1. Navegar a la carpeta backend:
   ```bash
   cd backend
   ```

2. Crear entorno virtual:
   ```bash
   python -m venv venv
   ```

3. Activar entorno virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

5. Ejecutar servidor:
   ```bash
   python main.py
   ```

   El servidor estará disponible en: http://localhost:8000
   Documentación API: http://localhost:8000/docs

### Frontend

1. Navegar a la carpeta frontend:
   ```bash
   cd frontend
   ```

2. Instalar dependencias:
   ```bash
   npm install
   ```

3. Ejecutar servidor de desarrollo:
   ```bash
   npm start
   ```

   La aplicación estará disponible en: http://localhost:3000

## Uso

1. **Registro/Login**: Accede al sistema con tus credenciales
2. **Dashboard**: Visualiza proyectos recientes y herramientas
3. **Nuevo Proyecto**: Crea nuevos diseños estructurales
4. **Editor**: Utiliza las herramientas de diseño
5. **Sincronización**: Conecta con Revit y AutoCAD

## Tecnologías Utilizadas

### Frontend
- React 18
- Material-UI (MUI)
- React Router DOM
- Axios para peticiones HTTP
- React Hook Form + Zod para validación
- Framer Motion para animaciones
- React Hot Toast para notificaciones

### Backend
- FastAPI
- Uvicorn (servidor ASGI)
- SQLAlchemy (ORM)
- Pydantic (validación de datos)
- Python-JOSE (JWT)
- CORS middleware

## Variables de Entorno

### Backend (.env)
```
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=sqlite:///./design_tools.db
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## API Endpoints

- `GET /` - Información de la API
- `GET /health` - Estado del servidor
- `POST /users/` - Crear usuario
- `POST /token` - Obtener token JWT
- `POST /designs/` - Crear diseño
- `GET /designs/` - Obtener diseños del usuario

## Desarrollo

### Próximas Características
- [ ] Editor de planos integrado
- [ ] Sincronización en tiempo real
- [ ] Exportación a formatos CAD
- [ ] Colaboración en equipo
- [ ] Historial de versiones
- [ ] Plantillas predefinidas

### Scripts Disponibles

#### Frontend
- `npm start` - Servidor de desarrollo
- `npm build` - Build para producción
- `npm test` - Ejecutar tests

#### Backend
- `python main.py` - Iniciar servidor

## Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT.

## Contacto

Proyecto desarrollado para Design Tools.

---

**Nota**: Este es un proyecto de demostración. Para uso en producción, asegúrate de configurar adecuadamente las variables de entorno y la seguridad.