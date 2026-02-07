# FHIR Constants
FHIR_RESOURCE_TYPES = [
    'Patient',
    'Observation',
    'DiagnosticReport',
    'Condition',
    'Medication',
    'AllergyIntolerance',
    'Bundle',
    'Practitioner',
    'Organization'
]

FHIR_OBSERVATION_CATEGORIES = [
    'vital-signs',
    'laboratory',
    'imaging',
    'procedure',
    'survey',
    'exam',
    'therapy',
    'activity'
]

FHIR_DIAGNOSTIC_REPORT_CATEGORIES = [
    'LAB',  # Laboratory
    'RAD',  # Radiology
    'CARD', # Cardiology
    'PATH', # Pathology
    'OTHER' # Other
]

FHIR_PATIENT_GENDERS = [
    'male',
    'female',
    'other',
    'unknown'
]

FHIR_OBSERVATION_STATUS = [
    'registered',
    'preliminary',
    'final',
    'amended',
    'corrected',
    'cancelled',
    'entered-in-error',
    'unknown'
]

FHIR_DIAGNOSTIC_REPORT_STATUS = [
    'registered',
    'partial',
    'preliminary',
    'final',
    'amended',
    'corrected',
    'appended',
    'cancelled',
    'entered-in-error',
    'unknown'
]

# LOINC and UCUM Constants
LOINC_SYSTEM_URL = "http://loinc.org"
UCUM_SYSTEM_URL = "http://unitsofmeasure.org"

# Common LOINC codes for blood work
COMMON_LOINC_CODES = {
    'glucose': '2339-0',
    'creatinine': '2160-0',
    'urea_nitrogen': '3094-0',
    'sodium': '2947-0',
    'potassium': '2823-3',
    'chloride': '2069-3',
    'co2': '20565-8',
    'calcium': '49765-1',
    'albumin': '1751-7',
    'protein': '2885-2',
    'alt': '1742-6',
    'ast': '1920-8',
    'alk_phosphatase': '6768-6',
    'bilirubin_total': '1975-2',
    'bilirubin_direct': '1968-7',
    'hgb': '718-7',
    'hct': '4544-3',
    'rbc': '789-8',
    'mcv': '787-2',
    'mch': '785-6',
    'mchc': '786-4',
    'rdw': '788-0',
    'wbc': '6690-2',
    'platelet': '777-3',
    'tsh': '3016-3',
    't3': '8025-5',
    't4': '3024-7'
}

# Common UCUM units
COMMON_UCUM_UNITS = {
    'mmol/L': 'mmol/L',
    'mg/dL': 'mg/dL',
    'g/dL': 'g/dL',
    'U/L': 'U/L',
    'mg/L': 'mg/L',
    'ng/mL': 'ng/mL',
    'pg/mL': 'pg/mL',
    'fL': 'fL',
    'umol/L': 'umol/L',
    'ng/dL': 'ng/dL'
}

# Interpretation codes
INTERPRETATION_CODES = {
    'L': 'Low',
    'H': 'High',
    'N': 'Normal',
    'A': 'Abnormal',
    'AA': 'Critical abnormal'
}

# Configuration defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_FILE_TYPES = ['pdf', 'jpg', 'jpeg', 'png']

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes
SESSION_TIMEOUT = 3600  # 1 hour
PASSWORD_MIN_LENGTH = 8

# AI Provider Types
AI_PROVIDERS = [
    'openai',
    'ollama',
    'lmstudio',
    'mock'
]

# Maximum number of patients allowed
MAX_PATIENTS = 4