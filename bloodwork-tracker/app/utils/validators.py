from typing import Dict, Any, List
from datetime import datetime


def validate_fhir_resource(resource: Dict[str, Any], resource_type: str) -> List[str]:
    """
    Basic validation for FHIR resources
    Returns a list of validation errors
    """
    errors = []
    
    if 'resourceType' not in resource:
        errors.append("Missing required field: resourceType")
        return errors
    
    if resource['resourceType'] != resource_type:
        errors.append(f"Expected resourceType '{resource_type}', got '{resource['resourceType']}'")
    
    # Specific validations based on resource type
    if resource_type == 'Patient':
        if 'name' not in resource:
            errors.append("Patient resource requires 'name' field")
        if 'id' not in resource and 'identifier' not in resource:
            errors.append("Patient resource requires either 'id' or 'identifier' field")
    
    elif resource_type == 'Observation':
        if 'status' not in resource:
            errors.append("Observation resource requires 'status' field")
        if 'code' not in resource:
            errors.append("Observation resource requires 'code' field")
        if 'subject' not in resource:
            errors.append("Observation resource requires 'subject' field")
        if 'effectiveDateTime' not in resource and 'effectivePeriod' not in resource:
            errors.append("Observation resource requires 'effectiveDateTime' or 'effectivePeriod' field")
    
    elif resource_type == 'DiagnosticReport':
        if 'status' not in resource:
            errors.append("DiagnosticReport resource requires 'status' field")
        if 'code' not in resource:
            errors.append("DiagnosticReport resource requires 'code' field")
        if 'subject' not in resource:
            errors.append("DiagnosticReport resource requires 'subject' field")
    
    elif resource_type == 'Bundle':
        if 'type' not in resource:
            errors.append("Bundle resource requires 'type' field")
        if 'entry' not in resource:
            errors.append("Bundle resource requires 'entry' field")
    
    return errors


def validate_date_format(date_string: str) -> bool:
    """
    Validates if a string is in proper date format (YYYY-MM-DD)
    """
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_datetime_format(datetime_string: str) -> bool:
    """
    Validates if a string is in proper datetime format (ISO 8601)
    """
    try:
        datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


def validate_loinc_code(code: str) -> bool:
    """
    Basic validation for LOINC codes
    LOINC codes typically follow patterns like: 12345-6 or 123456-7
    """
    import re
    pattern = r'^\d{4,7}-\d$'
    return bool(re.match(pattern, code))


def validate_ucum_unit(unit: str) -> bool:
    """
    Basic validation for UCUM units
    This is a simplified validation - in reality, UCUM has a complex grammar
    """
    # Just check if it's a non-empty string
    return bool(unit and isinstance(unit, str) and len(unit.strip()) > 0)


def validate_reference_range(ref_min: float, ref_max: float) -> bool:
    """
    Validates that reference range values make sense
    """
    if ref_min is None or ref_max is None:
        return True  # Allow partial ranges
    
    return ref_min < ref_max


def validate_observation_value(value: float, ref_min: float = None, ref_max: float = None) -> Dict[str, Any]:
    """
    Validates an observation value against reference ranges
    Returns a dictionary with validation results
    """
    result = {
        'valid': True,
        'interpretation': None,
        'issues': []
    }
    
    if ref_min is not None and ref_max is not None:
        if value < ref_min:
            result['interpretation'] = 'L'  # Low
        elif value > ref_max:
            result['interpretation'] = 'H'  # High
        else:
            result['interpretation'] = 'N'  # Normal
    elif ref_min is not None and value < ref_min:
        result['interpretation'] = 'L'  # Low
        result['issues'].append('Value below minimum reference range')
    elif ref_max is not None and value > ref_max:
        result['interpretation'] = 'H'  # High
        result['issues'].append('Value above maximum reference range')
    
    return result