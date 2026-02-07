from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime
import uuid


# Patient Schemas
class PatientBase(BaseModel):
    name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    notes: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    notes: Optional[str] = None


class PatientResponse(PatientBase):
    id: int
    fhir_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# LOINC Code Schemas
class LOINCCodeBase(BaseModel):
    code: str
    display: str
    system: str = "http://loinc.org"
    component: Optional[str] = None
    property: Optional[str] = None
    time_aspect: Optional[str] = None
    system_analyzed: Optional[str] = None
    scale_type: Optional[str] = None


class LOINCCodeCreate(LOINCCodeBase):
    pass


class LOINCCodeResponse(LOINCCodeBase):
    id: int

    class Config:
        from_attributes = True


# UCUM Unit Schemas
class UCUMUnitBase(BaseModel):
    code: str
    display: str
    system: str = "http://unitsofmeasure.org"


class UCUMUnitCreate(UCUMUnitBase):
    pass


class UCUMUnitResponse(UCUMUnitBase):
    id: int

    class Config:
        from_attributes = True


# Biomarker Schemas
class BiomarkerBase(BaseModel):
    name: str
    loinc_code_id: Optional[int] = None
    ucum_unit_id: Optional[int] = None
    default_ref_min: Optional[float] = None
    default_ref_max: Optional[float] = None


class BiomarkerCreate(BiomarkerBase):
    pass


class BiomarkerUpdate(BaseModel):
    name: Optional[str] = None
    loinc_code_id: Optional[int] = None
    ucum_unit_id: Optional[int] = None
    default_ref_min: Optional[float] = None
    default_ref_max: Optional[float] = None


class BiomarkerResponse(BiomarkerBase):
    id: int

    class Config:
        from_attributes = True


# Test Report Schemas
class TestReportBase(BaseModel):
    patient_id: int
    effective_datetime: datetime
    status: str = "final"
    category: str = "laboratory"
    conclusion: Optional[str] = None
    conclusion_code: Optional[str] = None


class TestReportCreate(TestReportBase):
    pass


class TestReportUpdate(BaseModel):
    status: Optional[str] = None
    conclusion: Optional[str] = None
    conclusion_code: Optional[str] = None


class TestReportResponse(TestReportBase):
    id: int
    fhir_id: str
    issued: datetime

    class Config:
        from_attributes = True


# Observation Schemas
class ObservationBase(BaseModel):
    patient_id: int
    report_id: int
    biomarker_id: int
    effective_datetime: datetime
    value: float
    status: str = "final"
    category: str = "laboratory"
    unit: Optional[str] = None
    ref_min: Optional[float] = None
    ref_max: Optional[float] = None
    interpretation: Optional[str] = None
    notes: Optional[str] = None
    performer: Optional[str] = None
    specimen: Optional[str] = None
    method: Optional[str] = None


class ObservationCreate(ObservationBase):
    pass


class ObservationUpdate(BaseModel):
    value: Optional[float] = None
    status: Optional[str] = None
    unit: Optional[str] = None
    ref_min: Optional[float] = None
    ref_max: Optional[float] = None
    interpretation: Optional[str] = None
    notes: Optional[str] = None
    performer: Optional[str] = None
    specimen: Optional[str] = None
    method: Optional[str] = None


class ObservationResponse(ObservationBase):
    id: int
    fhir_id: str

    class Config:
        from_attributes = True


# Medical Document Schemas
class MedicalDocumentBase(BaseModel):
    patient_id: int
    filename: str
    filepath: str
    file_type: str
    file_size: int
    report_id: Optional[int] = None
    description: Optional[str] = None


class MedicalDocumentCreate(MedicalDocumentBase):
    pass


class MedicalDocumentResponse(MedicalDocumentBase):
    id: int
    fhir_id: str
    upload_date: datetime

    class Config:
        from_attributes = True


# User Schemas
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    role: str = "user"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# Authentication Schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# FHIR Bundle Schema
class FHIRBundleEntry(BaseModel):
    fullUrl: Optional[str] = None
    resource: dict


class FHIRBundle(BaseModel):
    resourceType: str = "Bundle"
    type: str
    entry: List[FHIRBundleEntry]


# AI Request Schema
class AIConsultRequest(BaseModel):
    question: str
    provider: str = "mock"
    context_type: str = "fhir_bundle"  # fhir_bundle, text_summary, raw_data


class AIConsultResponse(BaseModel):
    response: str
    provider_used: str
    timestamp: datetime


# Backup Schemas
class BackupCreateRequest(BaseModel):
    name: Optional[str] = None


class BackupResponse(BaseModel):
    id: str
    name: str
    size: int
    created_at: datetime
    path: str


# Analytics Schemas
class TrendQuery(BaseModel):
    patient_id: int
    biomarker_code: str
    period: str = "6m"  # 1m, 3m, 6m, 1y, etc.

    @field_validator('period')
    def validate_period(cls, v):
        valid_periods = ['1m', '3m', '6m', '1y', 'all']
        if v not in valid_periods:
            raise ValueError(f'Period must be one of {valid_periods}')
        return v


class TrendDataPoint(BaseModel):
    date: datetime
    value: float
    unit: Optional[str] = None
    ref_min: Optional[float] = None
    ref_max: Optional[float] = None
    interpretation: Optional[str] = None


class TrendResponse(BaseModel):
    biomarker_name: str
    unit: Optional[str] = None
    data_points: List[TrendDataPoint]