from app.models import Patient, Observation, TestReport
from app import db
from datetime import datetime


def generate_fhir_context(patient_id: int) -> dict:
    """
    Generate FHIR-compliant context for AI consumption
    Returns bundle with Patient, Observations, DiagnosticReports
    """
    # Get patient FHIR resource
    patient_fhir = get_patient_fhir(patient_id)
    
    # Get all observations FHIR resources
    observations_fhir = get_observations_fhir(patient_id)
    
    # Get all diagnostic reports FHIR resources
    reports_fhir = get_reports_fhir(patient_id)
    
    # Create bundle
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": patient_fhir},
            *[{"resource": obs} for obs in observations_fhir],
            *[{"resource": report} for report in reports_fhir]
        ]
    }
    
    # Generate text summary
    text_summary = generate_text_summary(bundle)
    
    return {
        "fhir_bundle": bundle,
        "text_summary": text_summary,
        "patient_id": patient_id
    }


def get_patient_fhir(patient_id: int) -> dict:
    """Get patient as FHIR resource"""
    patient = Patient.query.get(patient_id)
    if not patient:
        raise ValueError(f"Patient with ID {patient_id} not found")
    
    fhir_patient = {
        "resourceType": "Patient",
        "id": patient.fhir_id,
        "identifier": [
            {
                "use": "usual",
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical Record Number"
                        }
                    ]
                },
                "value": str(patient.id)
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "text": patient.name
            }
        ],
        "gender": patient.gender,
        "birthDate": patient.birth_date.isoformat() if patient.birth_date else None,
        "note": [
            {
                "text": patient.notes
            }
        ] if patient.notes else []
    }
    
    # Remove None values
    fhir_patient = {k: v for k, v in fhir_patient.items() if v is not None}
    return fhir_patient


def get_observations_fhir(patient_id: int) -> list:
    """Get all observations for a patient as FHIR resources"""
    observations = Observation.query.filter_by(patient_id=patient_id).all()
    fhir_observations = []
    
    for obs in observations:
        fhir_obs = {
            "resourceType": "Observation",
            "id": obs.fhir_id,
            "status": obs.status,
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": obs.category,
                            "display": "Laboratory"
                        }
                    ]
                }
            ],
            "code": {
                "coding": []
            },
            "subject": {
                "reference": f"Patient/{obs.patient.fhir_id}"
            },
            "effectiveDateTime": obs.effective_datetime.isoformat() if obs.effective_datetime else None,
            "valueQuantity": {
                "value": obs.value,
                "unit": obs.unit,
                "system": "http://unitsofmeasure.org",
                "code": obs.unit
            } if obs.value is not None else None,
            "referenceRange": [
                {
                    "low": {
                        "value": obs.ref_min,
                        "unit": obs.unit
                    } if obs.ref_min is not None else None,
                    "high": {
                        "value": obs.ref_max,
                        "unit": obs.unit
                    } if obs.ref_max is not None else None
                }
            ] if obs.ref_min is not None or obs.ref_max is not None else [],
            "interpretation": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": obs.interpretation,
                            "display": get_interpretation_display(obs.interpretation)
                        }
                    ]
                }
            ] if obs.interpretation else [],
            "note": [
                {
                    "text": obs.notes
                }
            ] if obs.notes else []
        }
        
        # Add LOINC code if available
        if obs.biomarker and obs.biomarker.loinc:
            fhir_obs["code"]["coding"].append({
                "system": "http://loinc.org",
                "code": obs.biomarker.loinc.code,
                "display": obs.biomarker.loinc.display
            })
        else:
            # Add a generic code if no LOINC is available
            fhir_obs["code"]["coding"].append({
                "system": "http://example.org/local-codes",
                "code": f"local-{obs.biomarker_id}",
                "display": obs.biomarker.name if obs.biomarker else "Unknown"
            })
        
        # Remove None values
        fhir_obs = {k: v for k, v in fhir_obs.items() if v is not None}
        fhir_observations.append(fhir_obs)
    
    return fhir_observations


def get_reports_fhir(patient_id: int) -> list:
    """Get all reports for a patient as FHIR resources"""
    reports = TestReport.query.filter_by(patient_id=patient_id).all()
    fhir_reports = []
    
    for report in reports:
        fhir_report = {
            "resourceType": "DiagnosticReport",
            "id": report.fhir_id,
            "status": report.status,
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                            "code": report.category.upper(),
                            "display": "Laboratory"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "24323-8",
                        "display": "Laboratory studies (set)"
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{report.patient.fhir_id}"
            },
            "effectiveDateTime": report.effective_datetime.isoformat() if report.effective_datetime else None,
            "issued": report.issued.isoformat() if report.issued else None,
            "result": [
                {
                    "reference": f"Observation/{obs.fhir_id}"
                } for obs in report.observations
            ] if report.observations else [],
            "conclusion": report.conclusion,
        }
        
        # Remove None values
        fhir_report = {k: v for k, v in fhir_report.items() if v is not None}
        fhir_reports.append(fhir_report)
    
    return fhir_reports


def get_interpretation_display(interp_code):
    """Get display text for interpretation codes"""
    interpretations = {
        'L': 'Low',
        'H': 'High',
        'N': 'Normal',
        'A': 'Abnormal',
        'AA': 'Critical abnormal'
    }
    return interpretations.get(interp_code, interp_code)


def generate_text_summary(bundle: dict) -> str:
    """
    Generate human-readable summary from FHIR bundle
    Format: Biomarker | Date | Value | Unit | Reference Range | Interpretation
    """
    summary = "RESUMEN ANALÍTICAS:\n\n"
    
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Observation":
            # Get the display name for the biomarker
            code_display = "Unknown"
            if "code" in resource and "coding" in resource["code"]:
                for coding in resource["code"]["coding"]:
                    if coding.get("system") == "http://loinc.org":
                        code_display = coding.get("display", code_display)
                        break
                    elif coding.get("system") == "http://example.org/local-codes":
                        code_display = coding.get("display", code_display)
                        break
            
            date = resource.get("effectiveDateTime", "")
            value = resource.get("valueQuantity", {}).get("value", "")
            unit = resource.get("valueQuantity", {}).get("unit", "")
            
            ref_range_info = ""
            ref_ranges = resource.get("referenceRange", [])
            if ref_ranges:
                ref_range = ref_ranges[0]
                low = ref_range.get("low", {}).get("value", "")
                high = ref_range.get("high", {}).get("value", "")
                ref_range_info = f"[{low}-{high}]"
            
            interpretation_info = ""
            interpretations = resource.get("interpretation", [])
            if interpretations:
                interpretation = interpretations[0]
                coding_list = interpretation.get("coding", [])
                if coding_list:
                    interpretation_info = coding_list[0].get("display", "")
            
            summary += f"{code_display} | {date} | {value} {unit} | {ref_range_info} | {interpretation_info}\n"
    
    return summary