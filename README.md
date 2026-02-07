# Blood Work Tracker

## 📋 Descripción
Aplicación web local para gestión integral de resultados analíticos y documentos clínicos con capacidades de IA híbrida (local/cloud) y soporte HL7 FHIR.

## 🎯 Características Principales
- ✅ Gestión de perfiles de pacientes (máx. 4)
- ✅ Almacenamiento local de PDFs y documentos
- ✅ Interoperabilidad HL7 FHIR completa
- ✅ IA local y cloud configurable
- ✅ Visualización de tendencias y análisis
- ✅ Sistema de alertas inteligente
- ✅ Backup y restauración automática
- ✅ Dockerización completa
- ✅ Seguridad y privacidad de datos médicos
- ✅ Compatible con estándares médicos (LOINC, UCUM, SNOMED CT)

## 🚀 Instalación

### Requisitos
- Python 3.10+
- Docker (opcional)
- Memoria RAM: 4GB mínimo recomendado
- Espacio disco: 2GB disponible

### Instalación Local
```bash
git clone <repo>
cd bloodwork-tracker
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus configuraciones
python run.py
```

### Docker
```bash
docker-compose up -d
# Acceder a http://localhost:5000
```

## 📖 Uso

### Configuración Inicial
1. Crear primer usuario admin (por defecto: admin/admin123)
2. Configurar proveedor IA en .env
3. Importar códigos LOINC/UCUM (opcional)
4. Configurar parámetros de seguridad

### Gestión de Pacientes
- Crear/Editar/Eliminar perfiles
- Asignar biomarcadores con códigos LOINC
- Establecer rangos de referencia
- Importar/exportar datos FHIR

### Importación de Analíticas
- Subir PDFs de laboratorio
- Crear observaciones manualmente
- Importar Bundle FHIR
- Validación automática de datos

### Visualización
- Gráficos de tendencias por biomarcador
- Comparación entre informes
- Alertas de valores fuera de rango
- Resúmenes clínicos

### Análisis con IA
- Consultas sobre tendencias históricas
- Interpretación de resultados
- Sugerencias clínicas (no diagnóstico)
- Integración con múltiples proveedores

## 🔌 API Reference

### Autenticación
```bash
POST /api/v1/auth/login
{
  "username": "admin",
  "password": "password"
}
```

### FHIR Endpoints
```bash
# Patient
GET /fhir/Patient/{id}
PUT /fhir/Patient/{id}
PATCH /fhir/Patient/{id}
DELETE /fhir/Patient/{id}

# Observation
GET /fhir/Observation?patient={id}&code={loinc}&date=ge{date}&date=le{date}
GET /fhir/Observation/{id}
POST /fhir/Observation
PUT /fhir/Observation/{id}
DELETE /fhir/Observation/{id}

# DiagnosticReport
GET /fhir/DiagnosticReport?patient={id}&_count=20&_page=1
GET /fhir/DiagnosticReport/{id}
POST /fhir/DiagnosticReport
PUT /fhir/DiagnosticReport/{id}
DELETE /fhir/DiagnosticReport/{id}

# Bundle
GET /fhir/Bundle?patient={id}&type=collection
POST /fhir/Bundle  # Import complete patient data

# Search LOINC/UCUM
GET /api/v1/codes/loinc?search={term}
GET /api/v1/codes/ucum?search={term}
```

### IA Consultation
```bash
POST /api/v1/ai/consult
{
  "question": "¿Cómo han evolucionado mis niveles de glucosa?",
  "provider": "local",
  "context_type": "fhir_bundle",
  "patient_id": 1
}
```

## 🔐 Seguridad
- JWT para autenticación
- AES-256 para encriptación en reposo
- RBAC para control de acceso
- Audit trail completo
- Validación de entradas
- Protección contra inyecciones SQL
- Sesiones seguras con expiración

## 🧪 Testing
```bash
# Ejecutar todos los tests
pytest tests/ -v

# Tests específicos
pytest tests/test_fhir_mapping.py -v
pytest tests/test_security.py -v
pytest tests/test_ai_integration.py -v

# Coverage
pytest tests/ -v --cov=app --cov-report=html
```

## 📊 FHIR Mapping

### Patient ↔ FHIR Patient
| Campo DB | FHIR Field | Tipo |
|----------|-----------|------|
| id | resource.id | string |
| name | name[0].text | string |
| birth_date | birthDate | date |
| gender | gender | code |
| notes | note[0].text | string |

### Observation ↔ FHIR Observation
| Campo DB | FHIR Field | Tipo |
|----------|-----------|------|
| value | valueQuantity.value | decimal |
| unit | valueQuantity.unit | string |
| ref_min | referenceRange[0].low.value | decimal |
| ref_max | referenceRange[0].high.value | decimal |
| interpretation | interpretation[0].coding[0].code | code |
| effective_datetime | effectiveDateTime | dateTime |
| status | status | code |

### DiagnosticReport ↔ FHIR DiagnosticReport
| Campo DB | FHIR Field | Tipo |
|----------|-----------|------|
| id | resource.id | string |
| status | status | code |
| effective_datetime | effectiveDateTime | dateTime |
| issued | issued | dateTime |
| conclusion | conclusion | string |
| patient_id | subject.reference | Reference(Patient) |

## 🤖 Configuración IA

### Local (Ollama)
```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
AI_SEND_TO_CLOUD=false
```

### Local (LM Studio)
```env
AI_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234
AI_SEND_TO_CLOUD=false
```

### Cloud (OpenAI)
```env
AI_PROVIDER=openai
AI_SEND_TO_CLOUD=true
OPENAI_API_KEY=tu-api-key
```

### Simulación (por defecto)
```env
AI_PROVIDER=mock
AI_SEND_TO_CLOUD=false
```

## 🐳 Docker
```bash
# Levantar servicios
docker-compose up -d

# Detener servicios
docker-compose down

# Ver logs
docker-compose logs -f

# Ver estado de contenedores
docker-compose ps

# Construir imágenes
docker-compose build
```

## 🏗️ Arquitectura

### Estructura de Proyecto
```
bloodwork-tracker/
├── app/
│   ├── __init__.py
│   ├── models.py              # Modelos SQLAlchemy
│   ├── schemas.py             # Pydantic schemas
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py           # Autenticación
│   │   ├── patients.py       # CRUD pacientes
│   │   ├── reports.py        # CRUD informes
│   │   ├── observations.py   # CRUD observaciones
│   │   ├── documents.py      # CRUD documentos
│   │   ├── fhir.py          # Endpoints FHIR
│   │   ├── analytics.py     # Analytics
│   │   ├── backup.py        # Backup/restore
│   │   └── ai.py            # IA endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── fhir_mapper.py   # Mapping relacional ↔ FHIR
│   │   ├── ai_provider.py   # Strategy pattern IA
│   │   ├── file_service.py  # Manejo de archivos
│   │   ├── backup_service.py # Backup automático
│   │   └── security.py      # Encriptación y seguridad
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py    # Validación FHIR
│   │   ├── helpers.py       # Funciones auxiliares
│   │   └── constants.py     # Constantes FHIR
│   └── templates/
│       ├── base.html
│       ├── auth/
│       ├── patients/
│       ├── reports/
│       ├── observations/
│       ├── documents/
│       ├── analytics/
│       └── ai/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_fhir_mapping.py
│   ├── test_api_endpoints.py
│   ├── test_security.py
│   ├── test_ai_integration.py
│   └── test_file_operations.py
├── requirements.txt
├── config.py
├── run.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## 📈 Funcionalidades Avanzadas

### Análisis de Tendencias
- Visualización de series temporales
- Comparación de múltiples biomarcadores
- Identificación de patrones
- Alertas personalizables

### Integración FHIR
- Exportación completa de datos
- Importación de Bundles
- Validación de recursos
- Conformidad con estándares HL7

### Gestión de Documentos
- Soporte para múltiples formatos
- OCR para extracción de datos
- Organización jerárquica
- Búsqueda avanzada

## 🛡️ Consideraciones de Seguridad

### Datos Sensibles
- Cifrado AES-256 para documentos
- Hash seguro para contraseñas (bcrypt)
- Auditoría de accesos
- Control de permisos granular

### Acceso
- Autenticación JWT con expiración
- Bloqueo de cuentas tras intentos fallidos
- Sesiones seguras
- Registro de actividad

## 🧪 Pruebas y Calidad

### Tipos de Pruebas
- Unitarias: modelos, servicios, utilidades
- Integración: endpoints API y FHIR
- Seguridad: autenticación y autorización
- Rendimiento: carga y concurrencia

### Cobertura
- Mínimo 80% de cobertura de código
- Pruebas de integración FHIR
- Validación de escenarios de error
- Pruebas de seguridad

## 📋 Mantenimiento

### Backup
- Automático diario
- Compresión de datos
- Rotación de archivos
- Verificación de integridad

### Actualizaciones
- Versionado semántico
- Migraciones de base de datos
- Documentación del cambio
- Pruebas de regresión

## 📝 Licencia
MIT License

## ⚠️ Disclaimer
Esta aplicación NO proporciona diagnósticos médicos. Solo ofrece resúmenes y orientaciones informativas. Consulte siempre con un profesional de la salud.