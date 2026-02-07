from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Patient, Observation, Biomarker, LOINCCode
from app.schemas import TrendQuery, TrendResponse, TrendDataPoint
from app import db
from datetime import datetime, timedelta
from typing import Dict, List
import calendar

bp = Blueprint('analytics', __name__, url_prefix='/api/v1/analytics')


@bp.route('/trends', methods=['GET'])
@jwt_required()
def get_trends():
    """Get trend data for a specific biomarker over time for a patient"""
    try:
        # Parse query parameters
        patient_id = request.args.get('patient', type=int)
        biomarker_code = request.args.get('biomarker')  # This could be LOINC code or biomarker name
        period = request.args.get('period', '6m')  # Default to 6 months
        
        if not patient_id or not biomarker_code:
            return jsonify({'error': 'Patient ID and biomarker code are required'}), 400
        
        # Validate patient exists
        patient = Patient.query.get_or_404(patient_id)
        
        # Find biomarker by LOINC code or name
        # First try to find by LOINC code
        loinc_code = LOINCCode.query.filter_by(code=biomarker_code).first()
        biomarker = None
        
        if loinc_code:
            biomarker = Biomarker.query.filter_by(loinc_code_id=loinc_code.id).first()
        
        # If not found by LOINC, try by biomarker name
        if not biomarker:
            biomarker = Biomarker.query.filter(
                db.func.lower(Biomarker.name) == db.func.lower(biomarker_code)
            ).first()
        
        if not biomarker:
            return jsonify({'error': 'Biomarker not found'}), 404
        
        # Calculate date range based on period
        end_date = datetime.now()
        start_date = end_date
        
        if period == '1m':
            start_date = end_date - timedelta(days=30)
        elif period == '3m':
            start_date = end_date - timedelta(days=90)
        elif period == '6m':
            start_date = end_date - timedelta(days=180)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == 'all':
            # Use the earliest observation date
            earliest_obs = db.session.query(
                db.func.min(Observation.effective_datetime)
            ).filter_by(biomarker_id=biomarker.id, patient_id=patient_id).scalar()
            if earliest_obs:
                start_date = earliest_obs
            else:
                start_date = end_date - timedelta(days=30)  # Default to 30 days if no data
        else:
            return jsonify({'error': 'Invalid period. Use: 1m, 3m, 6m, 1y, all'}), 400
        
        # Query observations for this biomarker and patient within the date range
        observations = Observation.query.filter(
            Observation.biomarker_id == biomarker.id,
            Observation.patient_id == patient_id,
            Observation.effective_datetime >= start_date,
            Observation.effective_datetime <= end_date
        ).order_by(Observation.effective_datetime.asc()).all()
        
        # Convert observations to trend data points
        data_points = []
        for obs in observations:
            data_points.append(TrendDataPoint(
                date=obs.effective_datetime,
                value=obs.value,
                unit=obs.unit,
                ref_min=obs.ref_min,
                ref_max=obs.ref_max,
                interpretation=obs.interpretation
            ))
        
        # Create response
        trend_response = TrendResponse(
            biomarker_name=biomarker.name,
            unit=biomarker.unit.display if biomarker.unit else None,
            data_points=data_points
        )
        
        return jsonify(trend_response.dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/comparisons', methods=['GET'])
@jwt_required()
def get_comparisons():
    """Compare observations between different reports or time periods"""
    patient_id = request.args.get('patient', type=int)
    baseline_report_id = request.args.get('baseline', type=int)  # Report to compare against
    
    if not patient_id:
        return jsonify({'error': 'Patient ID is required'}), 400
    
    try:
        # Validate patient exists
        patient = Patient.query.get_or_404(patient_id)
        
        if baseline_report_id:
            # Compare specific report with others
            baseline_report = TestReport.query.filter_by(
                id=baseline_report_id, 
                patient_id=patient_id
            ).first_or_404()
            
            # Get observations from baseline report
            baseline_obs = Observation.query.filter_by(
                report_id=baseline_report_id
            ).all()
            
            # Get other recent reports for comparison
            other_reports = TestReport.query.filter(
                TestReport.patient_id == patient_id,
                TestReport.id != baseline_report_id
            ).order_by(TestReport.effective_datetime.desc()).limit(5).all()
            
            comparisons = []
            for report in other_reports:
                report_obs = Observation.query.filter_by(
                    report_id=report.id
                ).all()
                
                # Match observations by biomarker
                matched_obs = []
                for baseline_o in baseline_obs:
                    for report_o in report_obs:
                        if baseline_o.biomarker_id == report_o.biomarker_id:
                            matched_obs.append({
                                'biomarker': baseline_o.biomarker.name,
                                'baseline_value': baseline_o.value,
                                'baseline_unit': baseline_o.unit,
                                'comparison_value': report_o.value,
                                'comparison_unit': report_o.unit,
                                'difference': report_o.value - baseline_o.value,
                                'baseline_date': baseline_o.effective_datetime.isoformat(),
                                'comparison_date': report_o.effective_datetime.isoformat()
                            })
                            break
                
                if matched_obs:
                    comparisons.append({
                        'report_id': report.id,
                        'report_date': report.effective_datetime.isoformat(),
                        'observations': matched_obs
                    })
            
            return jsonify({
                'baseline_report_id': baseline_report_id,
                'baseline_date': baseline_report.effective_datetime.isoformat(),
                'comparisons': comparisons
            }), 200
        else:
            # Compare latest report with previous one
            reports = TestReport.query.filter_by(
                patient_id=patient_id
            ).order_by(TestReport.effective_datetime.desc()).limit(2).all()
            
            if len(reports) < 2:
                return jsonify({'message': 'Not enough reports for comparison'}), 200
            
            latest_report, previous_report = reports[0], reports[1]
            
            # Get observations from both reports
            latest_obs = Observation.query.filter_by(
                report_id=latest_report.id
            ).all()
            
            previous_obs = Observation.query.filter_by(
                report_id=previous_report.id
            ).all()
            
            # Match observations by biomarker
            comparisons = []
            for latest_o in latest_obs:
                for previous_o in previous_obs:
                    if latest_o.biomarker_id == previous_o.biomarker_id:
                        comparisons.append({
                            'biomarker': latest_o.biomarker.name,
                            'previous_value': previous_o.value,
                            'previous_unit': previous_o.unit,
                            'latest_value': latest_o.value,
                            'latest_unit': latest_o.unit,
                            'difference': latest_o.value - previous_o.value,
                            'previous_date': previous_o.effective_datetime.isoformat(),
                            'latest_date': latest_o.effective_datetime.isoformat(),
                            'change_direction': 'increase' if latest_o.value > previous_o.value else 'decrease' if latest_o.value < previous_o.value else 'same'
                        })
                        break
            
            return jsonify({
                'latest_report_id': latest_report.id,
                'previous_report_id': previous_report.id,
                'latest_date': latest_report.effective_datetime.isoformat(),
                'previous_date': previous_report.effective_datetime.isoformat(),
                'comparisons': comparisons
            }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/summary/<int:patient_id>', methods=['GET'])
@jwt_required()
def get_patient_summary(patient_id):
    """Get a comprehensive summary of patient's analytics"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Count total reports
    total_reports = TestReport.query.filter_by(patient_id=patient_id).count()
    
    # Count total observations
    total_observations = Observation.query.filter_by(patient_id=patient_id).count()
    
    # Get biomarkers with abnormal values (outside reference range)
    abnormal_obs = Observation.query.filter(
        Observation.patient_id == patient_id,
        db.or_(
            Observation.value < Observation.ref_min,
            Observation.value > Observation.ref_max
        )
    ).all()
    
    # Group abnormal observations by biomarker
    abnormal_biomarkers = {}
    for obs in abnormal_obs:
        biomarker_name = obs.biomarker.name
        if biomarker_name not in abnormal_biomarkers:
            abnormal_biomarkers[biomarker_name] = {
                'count': 0,
                'values': [],
                'dates': []
            }
        abnormal_biomarkers[biomarker_name]['count'] += 1
        abnormal_biomarkers[biomarker_name]['values'].append(obs.value)
        abnormal_biomarkers[biomarker_name]['dates'].append(obs.effective_datetime.isoformat())
    
    # Get most recent report
    latest_report = TestReport.query.filter_by(patient_id=patient_id)\
        .order_by(TestReport.effective_datetime.desc()).first()
    
    # Get observations from latest report
    latest_observations = []
    if latest_report:
        latest_obs = Observation.query.filter_by(report_id=latest_report.id).all()
        for obs in latest_obs:
            latest_observations.append({
                'biomarker': obs.biomarker.name,
                'value': obs.value,
                'unit': obs.unit,
                'reference_range': f"{obs.ref_min} - {obs.ref_max}" if obs.ref_min and obs.ref_max else "N/A",
                'interpretation': obs.interpretation,
                'date': obs.effective_datetime.isoformat()
            })
    
    summary = {
        'patient': {
            'id': patient.id,
            'name': patient.name,
            'age': calculate_age(patient.birth_date) if patient.birth_date else 'Unknown'
        },
        'analytics': {
            'total_reports': total_reports,
            'total_observations': total_observations,
            'abnormal_findings': len(abnormal_biomarkers),
            'latest_report_date': latest_report.effective_datetime.isoformat() if latest_report else None,
            'latest_observations': latest_observations
        },
        'abnormal_biomarkers': abnormal_biomarkers
    }
    
    return jsonify(summary), 200


def calculate_age(birth_date):
    """Calculate age from birth date"""
    if not birth_date:
        return None
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age