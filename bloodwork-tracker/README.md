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

## 🚀 Instalación

### Requisitos
- Python 3.10+
- Docker (opcional)

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
1. Crear primer usuario admin
2. Configurar proveedor IA en .env
3. Importar códigos LOINC/UCUM (opcional)

### Gestión de Pacientes
- Crear/Editar/Eliminar perfiles
- Asignar biomarcadores con códigos LOINC
- Establecer rangos de referencia

### Importación de Analíticas
- Subir PDFs de laboratorio
- Crear observaciones manualmente
- Importar Bundle FHIR

### Visualización
- Gráficos de tendencias por biomarcador
- Comparación entre informes
- Alertas de valores fuera de rango

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
GET /fhir/Patient/{id}
GET /fhir/Observation?patient={id}
GET /fhir/DiagnosticReport?patient={id}
GET /fhir/Bundle?patient={id}
```

### IA Consultation
```bash
POST /api/v1/ai/consult
{
  "question": "¿Cómo han evolucionado mis niveles de glucosa?",
  "provider": "local",
  "context_type": "fhir_bundle"
}
```

## 🔐 Seguridad
- JWT para autenticación
- AES-256 para encriptación en reposo
- RBAC para control de acceso
- Audit trail completo

## 🧪 Testing
```bash
pytest tests/ -v --cov=app
```

## 📊 FHIR Mapping

### Patient ↔ FHIR Patient
| Campo DB | FHIR Field | Tipo |
|----------|-----------|------|
| id | resource.id | string |
| name | name[0].text | string |
| birth_date | birthDate | date |
| gender | gender | code |

### Observation ↔ FHIR Observation
| Campo DB | FHIR Field | Tipo |
|----------|-----------|------|
| value | valueQuantity.value | decimal |
| unit | valueQuantity.unit | string |
| ref_min | referenceRange[0].low.value | decimal |
| ref_max | referenceRange[0].high.value | decimal |
| interpretation | interpretation[0].coding[0].code | code |

## 🤖 Configuración IA

### Local (Ollama)
```env
AI_PROVIDER=local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### Cloud (OpenAI)
```env
AI_PROVIDER=openai
AI_SEND_TO_CLOUD=true
OPENAI_API_KEY=tu-api-key
```

## 🐳 Docker
```bash
docker-compose up -d
docker-compose down
docker-compose logs -f
```

## 📝 Licencia
MIT License

## ⚠️ Disclaimer
Esta aplicación NO proporciona diagnósticos médicos. Solo ofrece resúmenes y orientaciones informativas. Consulte siempre con un profesional de la salud.