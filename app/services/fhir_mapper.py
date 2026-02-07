from datetime import datetime
from app.models import Patient, Observation, TestReport, Biomarker, LOINCCode, UCUMUnit
from typing import Dict, Any, List


class FHIRMapper:
    """Service to map between relational models and FHIR resources"""
    
    @staticmethod
    def patient_to_fhir(patient: Patient) -> Dict[str, Any]:
        """Convert Patient model to FHIR Patient resource"""
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
            "name": [
                {
                    "use": "official",
                    "text": patient.name
                }
            ],
            "gender": patient.gender.lower() if patient.gender else None,
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

    @staticmethod
    def fhir_to_patient(fhir_patient: Dict[str, Any]) -> Patient:
        """Convert FHIR Patient resource to Patient model"""
        from app.models import Patient
        
        # Extract fields from FHIR resource
        name_entry = fhir_patient.get("name", [{}])[0] if fhir_patient.get("name") else {}
        name = name_entry.get("text") or name_entry.get("family", "") + " " + name_entry.get("given", [""])[0]
        
        patient = Patient(
            name=name.strip() or "Unknown Patient",
            gender=fhir_patient.get("gender"),
            birth_date=datetime.fromisoformat(fhir_patient["birthDate"]) if fhir_patient.get("birthDate") else None,
            notes=fhir_patient.get("note", [{}])[0].get("text") if fhir_patient.get("note") else None
        )
        
        # Use the existing fhir_id from the FHIR resource
        if "id" in fhir_patient:
            patient.fhir_id = fhir_patient["id"]
        
        return patient

    @staticmethod
    def observation_to_fhir(observation: Observation) -> Dict[str, Any]:
        """Convert Observation model to FHIR Observation resource"""
        # Get biomarker information
        biomarker = observation.biomarker
        loinc_code = biomarker.loinc if biomarker.loinc else None
        unit_info = biomarker.unit if biomarker.unit else None
        
        fhir_observation = {
            "resourceType": "Observation",
            "id": observation.fhir_id,
            "status": observation.status,
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": observation.category,
                            "display": observation.category.title()
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": loinc_code.system if loinc_code else "http://local/biomarkers",
                        "code": loinc_code.code if loinc_code else f"local:{biomarker.id}",
                        "display": loinc_code.display if loinc_code else biomarker.name
                    }
                ],
                "text": biomarker.name
            },
            "subject": {
                "reference": f"Patient/{observation.patient.fhir_id}"
            },
            "effectiveDateTime": observation.effective_datetime.isoformat(),
            "valueQuantity": {
                "value": observation.value,
                "unit": observation.unit or (unit_info.display if unit_info else ""),
                "system": unit_info.system if unit_info else "http://unitsofmeasure.org",
                "code": observation.unit or (unit_info.code if unit_info else "")
            } if observation.value is not None else None,
            "interpretation": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": observation.interpretation,
                            "display": FHIRMapper._get_interpretation_display(observation.interpretation)
                        }
                    ]
                }
            ] if observation.interpretation else [],
            "referenceRange": [
                {
                    "low": {
                        "value": observation.ref_min,
                        "unit": observation.unit or (unit_info.display if unit_info else ""),
                        "system": unit_info.system if unit_info else "http://unitsofmeasure.org",
                        "code": observation.unit or (unit_info.code if unit_info else "")
                    } if observation.ref_min is not None else None,
                    "high": {
                        "value": observation.ref_max,
                        "unit": observation.unit or (unit_info.display if unit_info else ""),
                        "system": unit_info.system if unit_info else "http://unitsofmeasure.org",
                        "code": observation.unit or (unit_info.code if unit_info else "")
                    } if observation.ref_max is not None else None
                }
            ] if observation.ref_min is not None or observation.ref_max is not None else [],
            "performer": [
                {
                    "display": observation.performer
                }
            ] if observation.performer else [],
            "specimen": {
                "display": observation.specimen
            } if observation.specimen else None,
            "method": {
                "text": observation.method
            } if observation.method else None,
            "note": [
                {
                    "text": observation.notes
                }
            ] if observation.notes else []
        }
        
        # Remove None values recursively
        fhir_observation = FHIRMapper._remove_none_values(fhir_observation)
        
        return fhir_observation

    @staticmethod
    def fhir_to_observation(fhir_observation: Dict[str, Any], patient_id: int, report_id: int) -> Observation:
        """Convert FHIR Observation resource to Observation model"""
        from app.models import Observation, Biomarker, LOINCCode
        
        # Extract value information
        value_quantity = fhir_observation.get("valueQuantity", {})
        value = value_quantity.get("value")
        unit = value_quantity.get("unit")
        
        # Extract reference range
        ref_ranges = fhir_observation.get("referenceRange", [])
        ref_min = None
        ref_max = None
        if ref_ranges:
            ref_range = ref_ranges[0]
            if "low" in ref_range:
                ref_min = ref_range["low"].get("value")
            if "high" in ref_range:
                ref_max = ref_range["high"].get("value")
        
        # Extract interpretation
        interpretations = fhir_observation.get("interpretation", [])
        interpretation = None
        if interpretations:
            interpretation = interpretations[0].get("coding", [{}])[0].get("code")
        
        # Find or create biomarker based on code
        code_info = fhir_observation.get("code", {})
        codings = code_info.get("coding", [])
        
        # Look for LOINC code specifically
        loinc_code = None
        for coding in codings:
            if coding.get("system") == "http://loinc.org":
                loinc_code = coding.get("code")
                break
        
        # For now, we'll use a placeholder biomarker ID - in a real system we'd look up or create the biomarker
        # For this implementation, we'll create a temporary biomarker if needed
        biomarker_id = 1  # Placeholder - in real implementation, find or create biomarker
        
        observation = Observation(
            patient_id=patient_id,
            report_id=report_id,
            biomarker_id=biomarker_id,
            effective_datetime=datetime.fromisoformat(fhir_observation["effectiveDateTime"]),
            value=value,
            status=fhir_observation.get("status", "unknown"),
            category=FHIRMapper._extract_category(fhir_observation),
            unit=unit,
            ref_min=ref_min,
            ref_max=ref_max,
            interpretation=interpretation,
            notes=fhir_observation.get("note", [{}])[0].get("text") if fhir_observation.get("note") else None,
            performer=fhir_observation.get("performer", [{}])[0].get("display") if fhir_observation.get("performer") else None,
            specimen=fhir_observation.get("specimen", {}).get("display") if fhir_observation.get("specimen") else None,
            method=fhir_observation.get("method", {}).get("text") if fhir_observation.get("method") else None
        )
        
        # Use the existing fhir_id from the FHIR resource
        if "id" in fhir_observation:
            observation.fhir_id = fhir_observation["id"]
        
        return observation

    @staticmethod
    def report_to_fhir(report: TestReport) -> Dict[str, Any]:
        """Convert TestReport model to FHIR DiagnosticReport resource"""
        fhir_report = {
            "resourceType": "DiagnosticReport",
            "id": report.fhir_id,
            "status": report.status,
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                            "code": report.category,
                            "display": report.category.title()
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
                ],
                "text": "Laboratory Results"
            },
            "subject": {
                "reference": f"Patient/{report.patient.fhir_id}"
            },
            "effectiveDateTime": report.effective_datetime.isoformat(),
            "issued": report.issued.isoformat(),
            "result": [],  # This would be populated separately with references to observations
            "conclusion": report.conclusion,
            "conclusionCode": [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": report.conclusion_code,
                            "display": report.conclusion_code
                        }
                    ]
                }
            ] if report.conclusion_code else []
        }
        
        # Remove None values
        fhir_report = {k: v for k, v in fhir_report.items() if v is not None}
        
        return fhir_report

    @staticmethod
    def fhir_to_report(fhir_report: Dict[str, Any], patient_id: int) -> TestReport:
        """Convert FHIR DiagnosticReport resource to TestReport model"""
        from app.models import TestReport
        
        report = TestReport(
            patient_id=patient_id,
            effective_datetime=datetime.fromisoformat(fhir_report["effectiveDateTime"]),
            status=fhir_report.get("status", "unknown"),
            category=FHIRMapper._extract_diagnostic_category(fhir_report),
            conclusion=fhir_report.get("conclusion"),
            conclusion_code=fhir_report.get("conclusionCode", [{}])[0].get("coding", [{}])[0].get("code") if fhir_report.get("conclusionCode") else None
        )
        
        # Use the existing fhir_id from the FHIR resource
        if "id" in fhir_report:
            report.fhir_id = fhir_report["id"]
        
        return report

    @staticmethod
    def create_bundle(resources: List[Dict[str, Any]], bundle_type: str = "collection") -> Dict[str, Any]:
        """Create a FHIR Bundle resource from a list of resources"""
        bundle = {
            "resourceType": "Bundle",
            "type": bundle_type,
            "entry": []
        }
        
        for resource in resources:
            bundle["entry"].append({
                "fullUrl": f"{resource['resourceType']}/{resource['id']}" if 'id' in resource else None,
                "resource": resource
            })
        
        # Remove None values
        bundle["entry"] = [entry for entry in bundle["entry"] if entry["fullUrl"] is not None]
        
        return bundle

    @staticmethod
    def _get_interpretation_display(interpretation_code: str) -> str:
        """Get display text for interpretation codes"""
        interpretations = {
            "H": "High",
            "L": "Low",
            "N": "Normal",
            "A": "Abnormal",
            "AA": "Critical abnormal"
        }
        return interpretations.get(interpretation_code, interpretation_code)

    @staticmethod
    def _extract_category(fhir_observation: Dict[str, Any]) -> str:
        """Extract category from FHIR observation"""
        categories = fhir_observation.get("category", [])
        if categories:
            codings = categories[0].get("coding", [])
            if codings:
                return codings[0].get("code", "laboratory")
        return "laboratory"

    @staticmethod
    def _extract_diagnostic_category(fhir_report: Dict[str, Any]) -> str:
        """Extract category from FHIR diagnostic report"""
        categories = fhir_report.get("category", [])
        if categories:
            codings = categories[0].get("coding", [])
            if codings:
                return codings[0].get("code", "laboratory")
        return "laboratory"

    @staticmethod
    def _remove_none_values(obj):
        """Recursively remove None values from dictionary and lists"""
        if isinstance(obj, dict):
            return {
                key: FHIRMapper._remove_none_values(value)
                for key, value in obj.items()
                if value is not None
            }
        elif isinstance(obj, list):
            return [FHIRMapper._remove_none_values(item) for item in obj if item is not None]
        else:
            return obj