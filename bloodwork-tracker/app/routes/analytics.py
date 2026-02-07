from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Patient, Observation, Biomarker, LOINCCode
from app import db
from datetime import datetime, timedelta
import statistics


bp = Blueprint('analytics', __name__)


@bp.route('/trends', methods=['GET'])
@jwt_required()
def get_trends():
    """Get trends for a specific patient and biomarker over time"""
    try:
        patient_id = request.args.get('patient', type=int)
        biomarker_code = request.args.get('biomarker')  # LOINC code
        period = request.args.get('period', '6m')  # Options: 1m, 3m, 6m, 1y, all
        
        if not patient_id:
            return jsonify({'error': 'Patient ID is required'}), 400
        
        # Validate patient exists
        patient = Patient.query.get_or_404(patient_id)
        
        # Build query for observations
        query = db.session.query(Observation).filter(Observation.patient_id == patient_id)
        
        # Filter by biomarker if specified
        if biomarker_code:
            query = query.join(Biomarker).join(LOINCCode).filter(LOINCCode.code == biomarker_code)
        
        # Filter by period
        if period != 'all':
            months = {'1m': 1, '3m': 3, '6m': 6, '1y': 12}.get(period, 6)
            start_date = datetime.utcnow() - timedelta(days=months*30)
            query = query.filter(Observation.effective_datetime >= start_date)
        
        observations = query.order_by(Observation.effective_datetime.asc()).all()
        
        if not observations:
            return jsonify({
                'biomarker': biomarker_code,
                'period': period,
                'data': [],
                'statistics': {}
            }), 200
        
        # Prepare chart data
        chart_data = {
            'labels': [obs.effective_datetime.strftime('%Y-%m-%d') for obs in observations],
            'datasets': [{
                'label': f'{observations[0].biomarker.name if observations[0].biomarker else "Biomarker"} Levels',
                'data': [float(obs.value) for obs in observations],
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'fill': False
            }]
        }
        
        # Calculate statistics
        values = [obs.value for obs in observations]
        stats = {
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'count': len(values)
        }
        
        # Add reference ranges if available
        if observations[0].biomarker and observations[0].biomarker.default_ref_min is not None and observations[0].biomarker.default_ref_max is not None:
            chart_data['datasets'].append({
                'label': 'Reference Range',
                'data': [
                    {
                        'y': observations[0].biomarker.default_ref_min,
                        'start': obs.effective_datetime.strftime('%Y-%m-%d'),
                        'end': obs.effective_datetime.strftime('%Y-%m-%d')
                    } for obs in observations
                ],
                'type': 'line',
                'borderColor': 'rgb(255, 99, 132)',
                'borderDash': [5, 5],
                'fill': False
            })
        
        return jsonify({
            'biomarker': biomarker_code,
            'period': period,
            'chart_data': chart_data,
            'statistics': stats
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/comparisons', methods=['GET'])
@jwt_required()
def get_comparisons():
    """Compare observations between different reports or time periods"""
    try:
        patient_id = request.args.get('patient', type=int)
        baseline_report_id = request.args.get('baseline', type=int)  # Report ID to compare against
        
        if not patient_id:
            return jsonify({'error': 'Patient ID is required'}), 400
        
        # Validate patient exists
        patient = Patient.query.get_or_404(patient_id)
        
        # Get all reports for the patient
        reports = patient.reports
        
        if not reports:
            return jsonify({'comparisons': []}), 200
        
        # Sort reports by date
        sorted_reports = sorted(reports, key=lambda x: x.effective_datetime)
        
        comparisons = []
        for i, report in enumerate(sorted_reports):
            report_data = {
                'report_id': report.id,
                'report_date': report.effective_datetime.isoformat(),
                'observations': []
            }
            
            for obs in report.observations:
                obs_data = {
                    'biomarker': {
                        'name': obs.biomarker.name if obs.biomarker else 'Unknown',
                        'loinc_code': obs.biomarker.loinc.code if obs.biomarker and obs.biomarker.loinc else None
                    },
                    'value': obs.value,
                    'unit': obs.unit,
                    'reference_range': {
                        'min': obs.ref_min,
                        'max': obs.ref_max
                    } if obs.ref_min is not None or obs.ref_max is not None else None,
                    'interpretation': obs.interpretation
                }
                report_data['observations'].append(obs_data)
            
            comparisons.append(report_data)
        
        # If a baseline report is specified, calculate changes
        if baseline_report_id:
            baseline_report = next((r for r in sorted_reports if r.id == baseline_report_id), None)
            if baseline_report:
                # Add comparison data to each report
                for comp in comparisons:
                    if comp['report_id'] != baseline_report_id:
                        # Calculate differences from baseline
                        baseline_obs_map = {obs.biomarker_id: obs for obs in baseline_report.observations}
                        
                        for obs in comp['observations']:
                            baseline_obs = baseline_obs_map.get(
                                next((b.id for b in patient.observations if 
                                      b.biomarker.name == obs['biomarker']['name']), None)
                            )
                            
                            if baseline_obs:
                                diff = obs['value'] - baseline_obs.value
                                obs['change_from_baseline'] = {
                                    'absolute': round(diff, 2),
                                    'percent': round(((obs['value'] - baseline_obs.value) / baseline_obs.value * 100), 2) if baseline_obs.value != 0 else 0
                                }
        
        return jsonify({
            'patient_id': patient_id,
            'baseline_report_id': baseline_report_id,
            'comparisons': comparisons
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500