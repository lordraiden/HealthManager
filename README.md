# Blood Work Tracker

## 📋 Description
Local web application for comprehensive management of laboratory results and clinical documents with hybrid AI capabilities (local/cloud) and HL7 FHIR support.

## 🎯 Key Features
- ✅ Patient profile management (up to 4 profiles)
- ✅ Local storage of PDFs and documents
- ✅ Complete HL7 FHIR interoperability
- ✅ Configurable local and cloud AI
- ✅ Trend visualization and analytics
- ✅ Smart alert system
- ✅ Automatic backup and restoration
- ✅ Full containerization with Docker

## 🚀 Installation

### Requirements
- Python 3.10+
- Docker and Docker Compose (optional but recommended)
- At least 4GB RAM for optimal performance
- 2GB free disk space minimum

### Local Installation
```bash
git clone <repo>
cd bloodwork-tracker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configurations
python run.py
```

### Docker Installation (Recommended)
The easiest way to run Blood Work Tracker is using Docker Compose. This ensures all dependencies are properly configured and isolated.

First, ensure you have Docker and Docker Compose installed:
```bash
# Check if Docker is installed
docker --version
# Check if Docker Compose is installed
docker-compose --version
```

Then run the application:
```bash
# Clone the repository
git clone <repo>
cd bloodwork-tracker

# Copy the example environment file
cp .env.example .env

# Edit the .env file to configure your settings
nano .env  # or use your preferred editor

# Start the services using Docker Compose
docker-compose up -d

# View logs to ensure everything started correctly
docker-compose logs -f

# Access the application at http://localhost:5000
```

### Docker Compose Configuration
The default `docker-compose.yml` includes:
- Main application service
- PostgreSQL database (for persistent data storage)
- Optional services for AI integration (when configured)

To customize your deployment, modify the `.env` file before starting the containers. The application will automatically initialize the database and create the necessary tables on first startup.

### Stopping and Managing Services
```bash
# Stop the services
docker-compose down

# Stop and remove volumes (removes all data)
docker-compose down -v

# View service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f app  # for the main application
docker-compose logs -f db   # for the database
```

## 📖 Usage

### Initial Setup
1. Create first admin user (default: admin/admin123)
2. Configure AI provider in .env
3. Import LOINC/UCUM codes (optional)

### Patient Management
- Create/Edit/Delete profiles
- Assign biomarkers with LOINC codes
- Set reference ranges

### Analytics Import
- Upload laboratory PDFs
- Create observations manually
- Import FHIR Bundle

### Visualization
- Trend charts by biomarker
- Report comparison
- Out-of-range value alerts

## 🔌 API Reference

### Authentication
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

### AI Consultation
```bash
POST /api/v1/ai/consult
{
  "question": "How have my glucose levels evolved?",
  "provider": "local",
  "context_type": "fhir_bundle",
  "patient_id": 1
}
```

## 🔐 Security
- JWT for authentication
- AES-256 for encryption at rest
- RBAC for access control
- Complete audit trail

## 🧪 Testing
```bash
pytest tests/ -v --cov=app
```

## 📊 FHIR Mapping

### Patient ↔ FHIR Patient
| DB Field | FHIR Field | Type |
|----------|------------|------|
| id | resource.id | string |
| name | name[0].text | string |
| birth_date | birthDate | date |
| gender | gender | code |

### Observation ↔ FHIR Observation
| DB Field | FHIR Field | Type |
|----------|------------|------|
| value | valueQuantity.value | decimal |
| unit | valueQuantity.unit | string |
| ref_min | referenceRange[0].low.value | decimal |
| ref_max | referenceRange[0].high.value | decimal |
| interpretation | interpretation[0].coding[0].code | code |

## 🤖 AI Configuration

### Local (Ollama)
```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### Local (LM Studio)
```env
AI_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234
```

### Cloud (OpenAI)
```env
AI_PROVIDER=openai
AI_SEND_TO_CLOUD=true
OPENAI_API_KEY=your-api-key
```

### Simulation (default)
```env
AI_PROVIDER=mock
AI_SEND_TO_CLOUD=false
```

## 🐳 Docker
For detailed Docker installation and management instructions, see the Installation section above.

Basic Docker Compose commands:
```bash
# Start all services in detached mode
docker-compose up -d

# Stop all services
docker-compose down

# View logs from all services
docker-compose logs -f

# View logs from specific service
docker-compose logs -f app  # for the main application
docker-compose logs -f db   # for the database
```

## 📝 License
MIT License

## ⚠️ Disclaimer
This application does NOT provide medical diagnoses. It only offers informative summaries and guidance. Always consult with a healthcare professional.
