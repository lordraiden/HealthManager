from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Float, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from app import db
import uuid


class Patient(db.Model):
    __tablename__ = 'patients'
    id = Column(Integer, primary_key=True)
    fhir_id = Column(String, unique=True)  # UUID4 for FHIR
    name = Column(String, nullable=False)
    birth_date = Column(Date)
    gender = Column(String(10))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relaciones
    reports = relationship("TestReport", back_populates="patient")
    observations = relationship("Observation", back_populates="patient")
    documents = relationship("MedicalDocument", back_populates="patient")

    def __init__(self, name, birth_date=None, gender=None, notes=None):
        self.name = name
        self.birth_date = birth_date
        self.gender = gender
        self.notes = notes
        self.fhir_id = str(uuid.uuid4())


class LOINCCode(db.Model):
    __tablename__ = 'loinc_codes'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    display = Column(String, nullable=False)
    system = Column(String, default="http://loinc.org")
    component = Column(String)
    property = Column(String)
    time_aspect = Column(String)
    system_analyzed = Column(String)
    scale_type = Column(String)
    biomarkers = relationship("Biomarker", back_populates="loinc")


class UCUMUnit(db.Model):
    __tablename__ = 'ucum_units'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    display = Column(String, nullable=False)
    system = Column(String, default="http://unitsofmeasure.org")
    biomarkers = relationship("Biomarker", back_populates="unit")


class Biomarker(db.Model):
    __tablename__ = 'biomarkers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    loinc_code_id = Column(Integer, ForeignKey('loinc_codes.id'), nullable=True)
    ucum_unit_id = Column(Integer, ForeignKey('ucum_units.id'), nullable=True)
    default_ref_min = Column(Float)
    default_ref_max = Column(Float)
    loinc = relationship("LOINCCode", back_populates="biomarkers")
    unit = relationship("UCUMUnit", back_populates="biomarkers")


class TestReport(db.Model):
    __tablename__ = 'test_reports'
    id = Column(Integer, primary_key=True)
    fhir_id = Column(String, unique=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    status = Column(String, default="final")
    category = Column(String, default="laboratory")
    effective_datetime = Column(DateTime, nullable=False)
    issued = Column(DateTime, default=datetime.utcnow)
    conclusion = Column(Text)
    conclusion_code = Column(String)
    patient = relationship("Patient", back_populates="reports")
    observations = relationship("Observation", back_populates="report")
    documents = relationship("MedicalDocument", back_populates="report")

    def __init__(self, patient_id, effective_datetime, status="final", category="laboratory", 
                 conclusion=None, conclusion_code=None):
        self.patient_id = patient_id
        self.effective_datetime = effective_datetime
        self.status = status
        self.category = category
        self.conclusion = conclusion
        self.conclusion_code = conclusion_code
        self.fhir_id = str(uuid.uuid4())


class Observation(db.Model):
    __tablename__ = 'observations'
    id = Column(Integer, primary_key=True)
    fhir_id = Column(String, unique=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    report_id = Column(Integer, ForeignKey('test_reports.id'), nullable=False)
    biomarker_id = Column(Integer, ForeignKey('biomarkers.id'), nullable=False)
    status = Column(String, default="final")
    category = Column(String, default="laboratory")
    effective_datetime = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String)
    ref_min = Column(Float)
    ref_max = Column(Float)
    interpretation = Column(String)  # L=low, N=normal, H=high
    notes = Column(Text)
    performer = Column(String)  # Laboratory
    specimen = Column(String)   # Sample type
    method = Column(String)     # Analytical technique
    patient = relationship("Patient", back_populates="observations")
    report = relationship("TestReport", back_populates="observations")
    biomarker = relationship("Biomarker")

    def __init__(self, patient_id, report_id, biomarker_id, effective_datetime, value,
                 status="final", category="laboratory", unit=None, ref_min=None, 
                 ref_max=None, interpretation=None, notes=None, performer=None, 
                 specimen=None, method=None):
        self.patient_id = patient_id
        self.report_id = report_id
        self.biomarker_id = biomarker_id
        self.effective_datetime = effective_datetime
        self.value = value
        self.status = status
        self.category = category
        self.unit = unit
        self.ref_min = ref_min
        self.ref_max = ref_max
        self.interpretation = interpretation
        self.notes = notes
        self.performer = performer
        self.specimen = specimen
        self.method = method
        self.fhir_id = str(uuid.uuid4())


class MedicalDocument(db.Model):
    __tablename__ = 'medical_documents'
    id = Column(Integer, primary_key=True)
    fhir_id = Column(String, unique=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    report_id = Column(Integer, ForeignKey('test_reports.id'), nullable=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    file_type = Column(String)  # pdf, jpg, png
    file_size = Column(Integer)
    upload_date = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    patient = relationship("Patient", back_populates="documents")
    report = relationship("TestReport", back_populates="documents")

    def __init__(self, patient_id, filename, filepath, file_type, file_size, 
                 report_id=None, description=None):
        self.patient_id = patient_id
        self.filename = filename
        self.filepath = filepath
        self.file_type = file_type
        self.file_size = file_size
        self.report_id = report_id
        self.description = description
        self.fhir_id = str(uuid.uuid4())


class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, unique=True)
    role = Column(String, default="user")  # admin, user
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    def __init__(self, username, password_hash, email=None, role="user"):
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.role = role