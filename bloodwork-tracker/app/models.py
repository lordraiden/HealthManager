from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import uuid4
import os
from app import db


def generate_uuid():
    return str(uuid4())


class Patient(db.Model):
    __tablename__ = 'patients'
    id = Column(Integer, primary_key=True)
    fhir_id = Column(String, unique=True, default=generate_uuid)  # UUID4 for FHIR
    name = Column(String, nullable=False)
    birth_date = Column(Date)
    gender = Column(String(10))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    reports = relationship("TestReport", back_populates="patient")
    observations = relationship("Observation", back_populates="patient")
    documents = relationship("MedicalDocument", back_populates="patient")


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
    fhir_id = Column(String, unique=True, default=generate_uuid)
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


class Observation(db.Model):
    __tablename__ = 'observations'
    id = Column(Integer, primary_key=True)
    fhir_id = Column(String, unique=True, default=generate_uuid)
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
    performer = Column(String)  # Laboratorio
    specimen = Column(String)   # Tipo de muestra
    method = Column(String)     # Técnica analítica
    patient = relationship("Patient", back_populates="observations")
    report = relationship("TestReport", back_populates="observations")
    biomarker = relationship("Biomarker")


class MedicalDocument(db.Model):
    __tablename__ = 'medical_documents'
    id = Column(Integer, primary_key=True)
    fhir_id = Column(String, unique=True, default=generate_uuid)
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


class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, unique=True)
    role = Column(String, default="user")  # admin, user
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)