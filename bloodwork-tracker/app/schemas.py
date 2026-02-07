from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List
from enum import Enum


class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"


class PatientCreate(BaseModel):
    name: str
    birth_date: Optional[date] = None
    gender: Optional[GenderEnum] = None
    notes: Optional[str] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[GenderEnum] = None
    notes: Optional[str] = None


class PatientResponse(PatientCreate):
    id: int
    fhir_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LOINCCodeCreate(BaseModel):
    code: str
    display: str
    system: str = "http://loinc.org"
    component: Optional[str] = None
    property: Optional[str] = None
    time_aspect: Optional[str] = None
    system_analyzed: Optional[str] = None
    scale_type: Optional[str] = None


class LOINCCodeResponse(LOINCCodeCreate):
    id: int

    class Config:
        from_attributes = True


class UCUMUnitCreate(BaseModel):
    code: str
    display: str
    system: str = "http://unitsofmeasure.org"


class UCUMUnitResponse(UCUMUnitCreate):
    id: int

    class Config:
        from_attributes = True


class BiomarkerCreate(BaseModel):
    name: str
    loinc_code_id: Optional[int] = None
    ucum_unit_id: Optional[int] = None
    default_ref_min: Optional[float] = None
    default_ref_max: Optional[float] = None


class BiomarkerResponse(BiomarkerCreate):
    id: int

    class Config:
        from_attributes = True


class TestReportCreate(BaseModel):
    patient_id: int
    status: str = "final"
    category: str = "laboratory"
    effective_datetime: datetime
    conclusion: Optional[str] = None
    conclusion_code: Optional[str] = None


class TestReportUpdate(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    effective_datetime: Optional[datetime] = None
    conclusion: Optional[str] = None
    conclusion_code: Optional[str] = None


class TestReportResponse(TestReportCreate):
    id: int
    fhir_id: str
    issued: datetime

    class Config:
        from_attributes = True


class ObservationCreate(BaseModel):
    patient_id: int
    report_id: int
    biomarker_id: int
    status: str = "final"
    category: str = "laboratory"
    effective_datetime: datetime
    value: float
    unit: Optional[str] = None
    ref_min: Optional[float] = None
    ref_max: Optional[float] = None
    interpretation: Optional[str] = None  # L=low, N=normal, H=high
    notes: Optional[str] = None
    performer: Optional[str] = None
    specimen: Optional[str] = None
    method: Optional[str] = None


class ObservationUpdate(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    effective_datetime: Optional[datetime] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    ref_min: Optional[float] = None
    ref_max: Optional[float] = None
    interpretation: Optional[str] = None
    notes: Optional[str] = None
    performer: Optional[str] = None
    specimen: Optional[str] = None
    method: Optional[str] = None


class ObservationResponse(ObservationCreate):
    id: int
    fhir_id: str

    class Config:
        from_attributes = True


class MedicalDocumentCreate(BaseModel):
    patient_id: int
    report_id: Optional[int] = None
    filename: str
    filepath: str
    file_type: str
    file_size: Optional[int] = None
    description: Optional[str] = None


class MedicalDocumentResponse(MedicalDocumentCreate):
    id: int
    fhir_id: str
    upload_date: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    role: str = "user"


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class FHIRObservationComponent(BaseModel):
    code: dict
    valueQuantity: dict


class FHIRObservation(BaseModel):
    resourceType: str = "Observation"
    id: Optional[str] = None
    status: str = "final"
    category: List[dict] = [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}]
    code: dict
    subject: dict
    effectiveDateTime: Optional[str] = None
    issued: Optional[str] = None
    valueQuantity: Optional[dict] = None
    referenceRange: Optional[List[dict]] = None
    interpretation: Optional[List[dict]] = None
    note: Optional[List[dict]] = None


class FHIRPatient(BaseModel):
    resourceType: str = "Patient"
    id: Optional[str] = None
    identifier: Optional[List[dict]] = None
    active: bool = True
    name: List[dict]
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    telecom: Optional[List[dict]] = None
    address: Optional[List[dict]] = None
    maritalStatus: Optional[dict] = None
    communication: Optional[List[dict]] = None


class FHIRDiagnosticReport(BaseModel):
    resourceType: str = "DiagnosticReport"
    id: Optional[str] = None
    status: str = "final"
    category: List[dict] = [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "LAB", "display": "Laboratory"}]}]
    code: dict
    subject: dict
    effectiveDateTime: Optional[str] = None
    issued: Optional[str] = None
    performer: Optional[List[dict]] = None
    result: Optional[List[dict]] = None
    conclusion: Optional[str] = None
    conclusionCode: Optional[List[dict]] = None


class FHIRBundleEntry(BaseModel):
    fullUrl: Optional[str] = None
    resource: dict


class FHIRBundle(BaseModel):
    resourceType: str = "Bundle"
    id: Optional[str] = None
    type: str = "collection"
    entry: List[FHIRBundleEntry] = []


class AIConsultRequest(BaseModel):
    question: str
    provider: str = "local"
    context_type: str = "fhir_bundle"  # fhir_bundle, text_summary, raw_data


class AIConsultResponse(BaseModel):
    answer: str
    provider_used: str
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None