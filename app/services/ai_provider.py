from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests
import openai
from app import db
from app.models import Patient, Observation, TestReport
from app.services.fhir_mapper import FHIRMapper


class AIProvider(ABC):
    @abstractmethod
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        openai.api_key = api_key
    
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un asistente médico útil que ayuda a interpretar resultados de análisis clínicos. Proporciona información clara y precisa basada en los datos proporcionados. Recuerda que esta información es solo para fines informativos y no reemplaza la opinión médica profesional."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def get_name(self) -> str:
        return "OpenAI"


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url.rstrip('/')
        self.model = model
    
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"Eres un asistente médico útil que ayuda a interpretar resultados de análisis clínicos. Proporciona información clara y precisa basada en los datos proporcionados. Recuerda que esta información es solo para fines informativos y no reemplaza la opinión médica profesional.\n\n{prompt}",
                    "stream": False
                },
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                return response.json()["response"].strip()
            else:
                return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def get_name(self) -> str:
        return "Ollama"


class LMStudioProvider(AIProvider):
    def __init__(self, base_url: str = "http://localhost:1234"):
        self.base_url = base_url.rstrip('/')
    
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": "",  # LM Studio usually ignores this
                    "messages": [
                        {"role": "system", "content": "Eres un asistente médico útil que ayuda a interpretar resultados de análisis clínicos. Proporciona información clara y precisa basada en los datos proporcionados. Recuerda que esta información es solo para fines informativos y no reemplaza la opinión médica profesional."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            else:
                return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def get_name(self) -> str:
        return "LM Studio"


class MockProvider(AIProvider):
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        return "Este es un mensaje de respuesta simulado para fines de prueba. En una implementación real, aquí se mostraría la respuesta generada por el modelo de IA seleccionado."
    
    def get_name(self) -> str:
        return "Mock"


def get_ai_provider(provider_name: str, **kwargs) -> AIProvider:
    """Factory function to get the appropriate AI provider"""
    if provider_name.lower() == 'openai':
        api_key = kwargs.get('api_key') or kwargs.get('OPENAI_API_KEY')
        model = kwargs.get('model', 'gpt-3.5-turbo')
        return OpenAIProvider(api_key=api_key, model=model)
    elif provider_name.lower() == 'ollama':
        base_url = kwargs.get('base_url', 'http://localhost:11434')
        model = kwargs.get('model', 'llama2')
        return OllamaProvider(base_url=base_url, model=model)
    elif provider_name.lower() == 'lmstudio':
        base_url = kwargs.get('base_url', 'http://localhost:1234')
        return LMStudioProvider(base_url=base_url)
    else:  # Default to mock
        return MockProvider()


def generate_fhir_context(patient_id: int) -> Dict[str, Any]:
    """
    Generate FHIR-compliant context for AI consumption
    Returns bundle with Patient, Observations, DiagnosticReports
    """
    # Get patient FHIR resource
    patient = Patient.query.get(patient_id)
    if not patient:
        return {"error": "Patient not found"}
    
    patient_fhir = FHIRMapper.patient_to_fhir(patient)
    
    # Get all observations FHIR resources
    observations = Observation.query.filter_by(patient_id=patient_id).all()
    observations_fhir = [FHIRMapper.observation_to_fhir(obs) for obs in observations]
    
    # Get all diagnostic reports FHIR resources
    reports = TestReport.query.filter_by(patient_id=patient_id).all()
    reports_fhir = [FHIRMapper.report_to_fhir(report) for report in reports]
    
    # Create bundle
    bundle_entries = [
        {"resource": patient_fhir},
        *[{"resource": obs} for obs in observations_fhir],
        *[{"resource": report} for report in reports_fhir]
    ]
    
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": bundle_entries
    }
    
    # Generate text summary
    text_summary = generate_text_summary(bundle)
    
    return {
        "fhir_bundle": bundle,
        "text_summary": text_summary,
        "patient_id": patient_id
    }


def generate_text_summary(bundle: Dict[str, Any]) -> str:
    """
    Generate human-readable summary from FHIR bundle
    Format: Biomarker | Date | Value | Unit | Reference Range | Interpretation
    """
    summary = "RESUMEN ANALÍTICAS:\n\n"
    
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Observation":
            code = resource.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
            date = resource.get("effectiveDateTime", "")
            value = resource.get("valueQuantity", {}).get("value", "")
            unit = resource.get("valueQuantity", {}).get("unit", "")
            ref_range = resource.get("referenceRange", [{}])[0]
            low = ref_range.get("low", {}).get("value", "")
            high = ref_range.get("high", {}).get("value", "")
            interpretation = ""
            if resource.get("interpretation"):
                interpretation = resource["interpretation"][0].get("coding", [{}])[0].get("display", "")
            
            summary += f"{code} | {date} | {value} {unit} | [{low}-{high}] | {interpretation}\n"
    
    return summary