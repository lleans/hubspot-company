from flask import request, send_file, Response
from flask_restx import Namespace, Resource, fields
from services.extraction_service import ExtractionService
from services.hubspot_api_service import HubSpotAPIService
from utils.exceptions import ExtractionServiceError, AuthenticationError, HubSpotAPIError
from utils.decorators import validate_and_sanitize_input
from models.database import check_db_connection, get_db_stats
from datetime import datetime, timezone
import io
import csv
# Import only the essential logging utilities
from loki_logger import setup_loki_logging, get_logger

# Get a logger for this module
logger = get_logger(__name__)

# Create namespace for API
scan_api = Namespace('scan', description='HubSpot Extraction Service API')

# Initialize service
extraction_service = ExtractionService()

# Define models for Swagger documentation
extraction_config_model = scan_api.model('ExtractionConfig', {
    'scanId': fields.String(required=True, description='Unique identifier for this extraction'),
    'type': fields.List(fields.String, description='Types of data to extract'),
    'auth': fields.Raw(description='Authentication configuration'),
    'extraction': fields.Raw(description='Extraction configuration'),
    'filters': fields.Raw(description='Data filters'),
    'options': fields.Raw(description='Extraction options')
})

extraction_start_model = scan_api.model('ExtractionStart', {
    'config': fields.Nested(extraction_config_model, required=True, description='Extraction configuration')
})

extraction_status_model = scan_api.model('ExtractionStatus', {
    'scanId': fields.String(description='Scan identifier'),
    'status': fields.String(description='Current scan status'),
    'progress': fields.String(description='Progress information'),  # Must be String, not Raw
    'startedAt': fields.String(description='Scan start time (ISO format)'),
    'estimatedCompletion': fields.String(description='Estimated completion time (ISO format)'),
    'message': fields.String(description='Status message'),
    'metadata': fields.String(description='Additional metadata')  # Must be String, not Raw
})

extraction_results_model = scan_api.model('ExtractionResults', {
    'scanId': fields.String(description='Scan identifier'),
    'status': fields.String(description='Scan status'),
    'total_records': fields.Integer(description='Total records extracted'),
    'extraction_summary': fields.Raw(description='Extraction summary'),
    'data': fields.Raw(description='Extracted data'),
    'metadata': fields.Raw(description='Extraction metadata')
})

error_model = scan_api.model('Error', {
    'error': fields.String(description='Error type'),
    'message': fields.String(description='Error message'),
    'details': fields.Raw(description='Additional error details'),
    'timestamp': fields.DateTime(description='Error timestamp')
})

health_model = scan_api.model('Health', {
    'status': fields.String(description='Overall health status'),
    'timestamp': fields.DateTime(description='Health check timestamp'),
    'service': fields.String(description='Service name'),
    'version': fields.String(description='Service version'),
    'checks': fields.Raw(description='Individual health checks'),
    'system_stats': fields.Raw(description='System statistics')
})

stats_model = scan_api.model('Stats', {
    'service': fields.Raw(description='Service information'),
    'extractions': fields.Raw(description='Extraction statistics'),
    'performance': fields.Raw(description='Performance metrics'),
    'system_resources': fields.Raw(description='System resource usage')
})

@scan_api.route('/start')
class ExtractionStart(Resource):
    @scan_api.doc('start_extraction')
    @scan_api.expect(extraction_start_model, validate=True)
    @scan_api.response(400, 'Invalid request data', error_model)
    @scan_api.response(401, 'Invalid HubSpot API token', error_model)
    @scan_api.response(409, 'Active extraction already exists', error_model)
    @scan_api.response(500, 'Internal server error', error_model)
    def post(self):
        """Start a new HubSpot extraction scan"""
        try:
            # Get request ID from headers or generate a new one
            request_id = request.headers.get('X-Request-ID', 'no-id')
            
            logger.info(f"POST /scan/start called", extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path
            })
            
            # Parse request data
            data = request.get_json() or {}
            config = data.get('config', {})
            
            # Extract required fields from new format
            scan_id = config.get('scanId')
            auth_config = config.get('auth', {})
            token = auth_config.get('accessToken', '')
            
            # Log starting extraction
            logger.info(f"Starting extraction for scan ID: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id,
                'token_provided': bool(token)
            })
            
            if not scan_id:
                logger.warning("Validation failed: scanId is required", extra={
                    'request_id': request_id
                })
                return {
                    'error': 'Validation failed',
                    'message': 'scanId is required in config',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 400
            
            if not token:
                logger.warning("Authentication failed: API token is required", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'Unauthorized',
                    'message': 'API token is required in auth.accessToken',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 401
            
            # Validate token format
            if len(token) < 10:
                logger.warning("Invalid token format", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'Unauthorized',
                    'message': 'Invalid token format. HubSpot API tokens must be at least 10 characters long.',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 401
            
            # Check for existing extraction
            existing_job = extraction_service.check_existing_extraction(scan_id)
            if existing_job and existing_job['status'] in ['pending', 'running']:
                logger.warning(f"Active extraction already exists for scan {scan_id}", extra={
                    'request_id': request_id, 
                    'scan_id': scan_id,
                    'existing_job_id': existing_job.get('id')
                })
                return {
                    'error': 'Conflict',
                    'message': f'Active extraction already exists for scan {scan_id}',
                    'details': {'existing_job_id': existing_job.get('id')},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 409
            
            # Start extraction
            job_id = extraction_service.start_extraction(
                connection_id=scan_id,
                api_token=token,
                config=config
            )
            
            # Log successful extraction start
            logger.info(f"Extraction started successfully for scan ID: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id,
                'job_id': job_id
            })
            
            return {
                'scanId': scan_id,
                'status': 'started',
                'message': 'Company deals extraction scan started successfully',
                'startedAt': datetime.now(timezone.utc).isoformat(),
                'metadata': {
                    'totalEstimatedRecords': 0,
                    'estimatedDuration': '5-10 minutes',
                    'extractionTypes': config.get('type', ['deals', 'companies'])
                }
            }, 202
            
        except AuthenticationError as e:
            # Log authentication error
            logger.error(f"Authentication error: {str(e)}", extra={
                'scan_id': scan_id if 'scan_id' in locals() else None,
                'error_type': 'AuthenticationError'
            })
            
            return {
                'error': 'Unauthorized',
                'message': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 401
            
        except ExtractionServiceError as e:
            error_type = 'DuplicateExtractionError' if 'already exists' in str(e) else 'ExtractionServiceError'
            status_code = 409 if 'already exists' in str(e) else 500
            
            logger.error(f"Extraction service error: {str(e)}", extra={
                'scan_id': scan_id if 'scan_id' in locals() else None,
                'error_type': error_type
            })
            
            return {
                'error': error_type,
                'message': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, status_code
            
        except Exception as e:
            logger.error(f"Unexpected error starting extraction: {str(e)}", 
                        extra={
                            'scan_id': scan_id if 'scan_id' in locals() else None,
                            'error_type': 'InternalServerError'
                        },
                        exc_info=True)
            
            return {
                'error': 'InternalServerError',
                'message': 'An unexpected error occurred',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 500

@scan_api.route('/status/<string:scan_id>')
class ExtractionStatus(Resource):
    @scan_api.doc('get_extraction_status')
    @scan_api.response(200, 'Status retrieved successfully')
    @scan_api.response(404, 'Scan not found', error_model)
    @scan_api.response(500, 'Internal server error', error_model)
    def get(self, scan_id):
        """Get extraction scan status"""
        try:
            # Get request ID from headers
            request_id = request.headers.get('X-Request-ID', 'no-id')
            
            logger.info(f"Checking status for scan: {scan_id}", extra={
                'request_id': request_id, 
                'scan_id': scan_id,
                'method': request.method
            })
            
            status = extraction_service.get_extraction_status_by_connection(scan_id)
            
            if not status or status.get('status') == 'not_found':
                logger.warning(f"Scan not found: {scan_id}", extra={
                    'request_id': request_id, 
                    'scan_id': scan_id
                })
                return {
                    'error': 'Scan Not Found',
                    'message': f'Scan {scan_id} not found',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 404
            
            # Log successful status retrieval
            logger.info(f"Status retrieved for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id,
                'status': status.get('status', 'unknown'),
                'progress': status.get('progress_percentage', 0)
            })
            
            # Convert to new format
            return {
                'scanId': scan_id,
                'status': status.get('status', 'unknown'),
                'progress': {
                    'percentage': status.get('progress_percentage', 0),
                    'recordsProcessed': status.get('total_records_extracted', 0),
                    'recordsTotal': status.get('total_records_extracted', 0),
                    'currentOperation': status.get('message', 'Processing...')
                },
                'startedAt': status.get('start_time'),
                'estimatedCompletion': status.get('end_time'),
                'message': status.get('message', ''),
                'metadata': {
                    'companiesExtracted': status.get('companies_extracted', 0),
                    'dealsExtracted': status.get('deals_extracted', 0),
                    'pipelinesExtracted': status.get('pipelines_extracted', 0)
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Failed to get extraction status for scan {scan_id}: {str(e)}", 
                        extra={'scan_id': scan_id},
                        exc_info=True)
            return {
                'error': 'InternalServerError',
                'message': 'Failed to get scan status',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 500

@scan_api.route('/result/<string:scan_id>')
class ExtractionResults(Resource):
    @scan_api.doc('get_extraction_results')
    # @scan_api.response(200, extraction_results_model)
    @scan_api.response(202, 'Scan not completed', error_model)
    @scan_api.response(404, 'Scan not found', error_model)
    @scan_api.response(500, 'Internal server error', error_model)
    def get(self, scan_id):
        """Get extraction results for a scan including stage history data"""
        try:
            # Get request ID
            request_id = request.headers.get('X-Request-ID', 'no-id')
            
            # Get pagination parameters
            limit = request.args.get('limit', 100, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            # Get analytics flag
            include_analytics = request.args.get('analytics', 'false').lower() == 'true'
            
            logger.info(f"Retrieving results for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id,
                'limit': limit,
                'offset': offset,
                'include_analytics': include_analytics
            })
            
            # Validate pagination
            if limit < 1 or limit > 1000:
                logger.warning(f"Invalid pagination: limit out of range ({limit})", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'ValidationError',
                    'message': 'Limit must be between 1 and 1000',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 400
            
            if offset < 0:
                logger.warning(f"Invalid pagination: negative offset ({offset})", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'ValidationError',
                    'message': 'Offset must be non-negative',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 400
            
            # Check if scan is completed
            status = extraction_service.get_extraction_status_by_connection(scan_id)
            if not status or status.get('status') == 'not_found':
                logger.warning(f"Scan not found: {scan_id}", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'Scan Not Found',
                    'message': f'Scan {scan_id} not found',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 404
            
            if status.get('status') not in ['completed']:
                logger.info(f"Scan not completed: {scan_id}, status: {status.get('status')}", extra={
                    'request_id': request_id,
                    'scan_id': scan_id,
                    'status': status.get('status')
                })
                return {
                    'error': 'Scan Not Completed',
                    'message': f'Scan {scan_id} is not completed. Current status: {status.get("status")}',
                    'details': {
                        'currentStatus': status.get('status'),
                        'progress': status.get('progress_percentage', 0)
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 202
            
            # Get results (with or without analytics)
            if include_analytics:
                logger.info(f"Including analytics for scan: {scan_id}", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                results = extraction_service.get_extraction_results_with_analytics_by_connection(scan_id)
            else:
                results = extraction_service.get_extraction_results_by_connection(scan_id)
            
            if not results:
                logger.warning(f"Results not found for scan: {scan_id}", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'ResultsNotFound',
                    'message': f'Results not found for scan {scan_id}',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 404
            
            # Extract data
            companies = results.get('companies', [])
            deals = results.get('deals', [])
            pipelines = results.get('pipelines', [])
            stage_history = results.get('stage_history', [])
            analytics = results.get('analytics', {})
            
            logger.info(f"Retrieved data for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id,
                'companies_count': len(companies),
                'deals_count': len(deals),
                'pipelines_count': len(pipelines),
                'stage_history_count': len(stage_history),
                'has_analytics': bool(analytics)
            })
            
            # Apply pagination to main data (companies, deals, pipelines)
            all_main_data = []
            for company in companies:
                all_main_data.append({**company, 'record_type': 'company'})
            for deal in deals:
                all_main_data.append({**deal, 'record_type': 'deal'})
            for pipeline in pipelines:
                all_main_data.append({**pipeline, 'record_type': 'pipeline'})
            
            paginated_main_data = all_main_data[offset:offset + limit]
            
            # Rebuild paginated main data structure
            paginated_companies = [item for item in paginated_main_data if item.get('record_type') == 'company']
            paginated_deals = [item for item in paginated_main_data if item.get('record_type') == 'deal']
            paginated_pipelines = [item for item in paginated_main_data if item.get('record_type') == 'pipeline']
            
            # For stage history, apply separate pagination if requested
            stage_history_offset = request.args.get('stage_offset', 0, type=int)
            stage_history_limit = request.args.get('stage_limit', 200, type=int)  # Default higher limit for stage history
            
            # Validate stage history pagination
            if stage_history_limit > 500:
                stage_history_limit = 500
            if stage_history_offset < 0:
                stage_history_offset = 0
            
            paginated_stage_history = stage_history[stage_history_offset:stage_history_offset + stage_history_limit]
            
            # Build response
            response_data = {
                'scanId': scan_id,
                'status': 'completed',
                'total_records': len(companies) + len(deals) + len(pipelines) + len(stage_history),
                'extraction_summary': {
                    'companies_count': len(companies),
                    'deals_count': len(deals),
                    'pipelines_count': len(pipelines),
                    'stage_history_count': len(stage_history),
                    'started_at': results.get('extraction_metadata', {}).get('start_time'),
                    'completed_at': results.get('extraction_metadata', {}).get('end_time'),
                    'duration_seconds': results.get('extraction_metadata', {}).get('duration_seconds')
                },
                'data': {
                    'companies': paginated_companies,
                    'deals': paginated_deals,
                    'pipelines': paginated_pipelines,
                    'stage_history': paginated_stage_history
                },
                'metadata': {
                    'pagination': {
                        'main_data': {
                            'offset': offset,
                            'limit': limit,
                            'total_records': len(all_main_data),
                            'returned_records': len(paginated_main_data)
                        },
                        'stage_history': {
                            'offset': stage_history_offset,
                            'limit': stage_history_limit,
                            'total_records': len(stage_history),
                            'returned_records': len(paginated_stage_history)
                        }
                    }
                }
            }
            
            # Add analytics if included
            if include_analytics and analytics:
                response_data['analytics'] = analytics
                
                # Add analytics summary to extraction_summary
                if 'velocity_metrics' in analytics:
                    velocity = analytics['velocity_metrics']
                    response_data['extraction_summary'].update({
                        'avg_deal_cycle_days': velocity.get('avg_cycle_time_days', 0),
                        'deals_analyzed': velocity.get('total_deals_analyzed', 0),
                        'velocity_distribution': velocity.get('velocity_distribution', {})
                    })
                
                # Add bottleneck info to summary
                if 'bottleneck_stages' in analytics and analytics['bottleneck_stages']:
                    top_bottleneck = analytics['bottleneck_stages'][0]
                    response_data['extraction_summary']['top_bottleneck'] = {
                        'stage_label': top_bottleneck.get('stage_label'),
                        'avg_duration_days': top_bottleneck.get('avg_duration_days')
                    }
            
            logger.info(f"Returning results for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id,
                'response_companies': len(paginated_companies),
                'response_deals': len(paginated_deals),
                'response_pipelines': len(paginated_pipelines),
                'response_stage_history': len(paginated_stage_history),
                'has_analytics': include_analytics and bool(analytics)
            })
            
            return response_data, 200
            
        except Exception as e:
            logger.error(f"Failed to get extraction results for scan {scan_id}: {str(e)}", 
                        extra={'scan_id': scan_id, 'request_id': request_id},
                        exc_info=True)
            return {
                'error': 'InternalServerError',
                'message': 'Failed to get extraction results',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 500

@scan_api.route('/download/<string:scan_id>')
class ExtractionDownload(Resource):
    @scan_api.doc('download_extraction_results')
    @scan_api.response(200, 'CSV file download')
    @scan_api.response(404, 'Scan not found or no data', error_model)
    @scan_api.response(500, 'Internal server error', error_model)
    def get(self, scan_id):
        """Download extraction results as CSV"""
        try:
            # Get request ID
            request_id = request.headers.get('X-Request-ID', 'no-id')
            
            logger.info(f"Processing download request for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id
            })
            
            # Get results
            results = extraction_service.get_extraction_results_by_connection(scan_id)
            if not results:
                logger.warning(f"No data found for download, scan: {scan_id}", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'Scan Not Found',
                    'message': f'Scan {scan_id} not found or contains no data',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 404
            
            # Create CSV content
            logger.info(f"Generating CSV for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id,
                'companies_count': len(results.get('companies', [])),
                'deals_count': len(results.get('deals', []))
            })
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'record_type', 'id', 'name', 'company', 'amount', 'stage', 
                'created_date', 'last_modified'
            ])
            
            # Write companies
            for company in results.get('companies', []):
                writer.writerow([
                    'company',
                    company.get('hubspot_company_id', ''),
                    company.get('name', ''),
                    company.get('domain', ''),
                    '',
                    '',
                    company.get('hubspot_created_date', ''),
                    company.get('hubspot_updated_date', '')
                ])
            
            # Write deals
            for deal in results.get('deals', []):
                writer.writerow([
                    'deal',
                    deal.get('hubspot_deal_id', ''),
                    deal.get('dealname', ''),
                    deal.get('company_name', ''),
                    deal.get('amount', ''),
                    deal.get('dealstage_label', ''),
                    deal.get('hubspot_created_date', ''),
                    deal.get('hubspot_updated_date', '')
                ])
            
            # Create file-like object
            output.seek(0)
            csv_content = output.getvalue()
            output.close()
            
            # Log successful CSV generation
            logger.info(f"CSV download ready for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id,
                'content_size': len(csv_content)
            })
            
            # Return as file download
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=hubspot_company_deals_{scan_id}.csv'
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to download results for scan {scan_id}: {str(e)}", 
                        extra={'scan_id': scan_id},
                        exc_info=True)
            return {
                'error': 'InternalServerError',
                'message': 'Failed to generate download',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 500

@scan_api.route('/cancel/<string:scan_id>')
class ExtractionCancel(Resource):
    @scan_api.doc('cancel_extraction')
    @scan_api.response(200, 'Scan cancelled successfully')
    @scan_api.response(400, 'Cannot cancel scan', error_model)
    @scan_api.response(404, 'Scan not found', error_model)
    @scan_api.response(500, 'Internal server error', error_model)
    def post(self, scan_id):
        """Cancel a running extraction scan"""
        try:
            # Get request ID
            request_id = request.headers.get('X-Request-ID', 'no-id')
            
            logger.info(f"Processing cancellation request for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id
            })
            
            # Check if scan exists and is cancellable
            status = extraction_service.get_extraction_status_by_connection(scan_id)
            if not status or status.get('status') == 'not_found':
                logger.warning(f"Cannot cancel: scan not found: {scan_id}", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'Scan Not Found',
                    'message': f'Scan {scan_id} not found',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 404
            
            if status.get('status') not in ['pending', 'running']:
                logger.warning(f"Cannot cancel: scan not in cancellable state: {scan_id}", extra={
                    'request_id': request_id,
                    'scan_id': scan_id,
                    'status': status.get('status')
                })
                return {
                    'error': 'Cannot Cancel',
                    'message': f'Scan {scan_id} cannot be cancelled (not found or not active)',
                    'details': {
                        'currentStatus': status.get('status'),
                        'reason': 'Scan not in cancellable state'
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 400
            
            # Cancel the scan
            logger.info(f"Cancelling extraction for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id
            })
            
            success = extraction_service.cancel_extraction_by_connection(scan_id)
            if not success:
                logger.error(f"Failed to cancel scan: {scan_id}", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'CancellationError',
                    'message': f'Failed to cancel scan {scan_id}',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 500
            
            # Log successful cancellation
            logger.info(f"Successfully cancelled scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id
            })
            
            return {
                'scanId': scan_id,
                'status': 'cancelled',
                'message': 'Company deals extraction scan cancelled successfully',
                'cancelledAt': datetime.now(timezone.utc).isoformat(),
                'metadata': {
                    'cancellationReason': 'User requested'
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Failed to cancel scan {scan_id}: {str(e)}", 
                        extra={'scan_id': scan_id},
                        exc_info=True)
            return {
                'error': 'InternalServerError',
                'message': f'Failed to cancel scan: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 500

@scan_api.route('/remove/<string:scan_id>')
class ExtractionRemove(Resource):
    @scan_api.doc('remove_extraction')
    @scan_api.response(200, 'Scan removed successfully')
    @scan_api.response(404, 'Scan not found', error_model)
    @scan_api.response(500, 'Internal server error', error_model)
    def delete(self, scan_id):
        """Remove an extraction scan and all associated data"""
        try:
            # Get request ID
            request_id = request.headers.get('X-Request-ID', 'no-id')
            
            logger.info(f"Processing removal request for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id
            })
            
            # Check if scan exists
            if not extraction_service.connection_exists(scan_id):
                logger.warning(f"Cannot remove: scan not found: {scan_id}", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'Scan Not Found',
                    'message': f'Scan {scan_id} not found',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 404
            
            # Delete the scan
            logger.info(f"Removing data for scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id
            })
            
            success = extraction_service.delete_extraction_by_connection(scan_id)
            if not success:
                logger.error(f"Failed to remove scan: {scan_id}", extra={
                    'request_id': request_id,
                    'scan_id': scan_id
                })
                return {
                    'error': 'DeletionError',
                    'message': f'Failed to remove scan {scan_id}',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, 500
            
            # Log successful removal
            logger.info(f"Successfully removed scan: {scan_id}", extra={
                'request_id': request_id,
                'scan_id': scan_id
            })
            
            return {
                'scanId': scan_id,
                'message': 'Company deals extraction scan and all associated data removed successfully',
                'removedAt': datetime.now(timezone.utc).isoformat()
            }, 200
            
        except Exception as e:
            logger.error(f"Failed to remove scan {scan_id}: {str(e)}", 
                        extra={'scan_id': scan_id},
                        exc_info=True)
            return {
                'error': 'InternalServerError',
                'message': f'Failed to remove scan: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 500

@scan_api.route('/stats')
class ServiceStats(Resource):
    @scan_api.doc('get_service_stats')
    @scan_api.marshal_with(stats_model)
    @scan_api.response(200, 'Statistics retrieved successfully')
    def get(self):
        """Get comprehensive service statistics"""
        try:
            # Get request ID
            request_id = request.headers.get('X-Request-ID', 'no-id')
            
            logger.info("Retrieving service statistics", extra={
                'request_id': request_id
            })
            
            from services.job_service import JobService
            job_service = JobService()
            
            # Get job statistics
            job_stats = job_service.get_job_statistics()
            
            # Get system stats
            thread_stats = extraction_service.get_thread_pool_stats()
            
            logger.info("Service statistics retrieved", extra={
                'request_id': request_id,
                'total_jobs': job_stats.get('total_jobs', 0),
                'active_threads': thread_stats.get('active_threads', 0)
            })
            
            return {
                'service': {
                    'name': 'HubSpot Company Deals Extraction Service',
                    'version': '2.0.0',
                    'uptime_seconds': 86400,  # Placeholder
                    'api_framework': 'Flask-RESTX'
                },
                'extractions': {
                    'total_scans': job_stats.get('total_jobs', 0),
                    'successful_scans': job_stats.get('completed_jobs', 0),
                    'failed_scans': job_stats.get('failed_jobs', 0),
                    'active_scans': job_stats.get('active_jobs', 0)
                },
                'performance': {
                    'average_scan_duration_seconds': job_stats.get('average_extraction_time', 0),
                    'total_records_extracted': 0,  # Would need to calculate
                    'success_rate': job_stats.get('success_rate', 0)
                },
                'system_resources': {
                    'active_threads': thread_stats.get('active_threads', 0),
                    'max_threads': thread_stats.get('max_workers', 0),
                    'pending_tasks': thread_stats.get('pending_tasks', 0)
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 200
            
        except Exception as e:
            logger.error(f"Failed to get service statistics: {str(e)}", exc_info=True)
            return {
                'error': 'InternalServerError',
                'message': 'Failed to get service statistics',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, 500

@scan_api.route('/health')
class HealthCheck(Resource):
    @scan_api.doc('health_check')
    @scan_api.marshal_with(health_model)
    @scan_api.response(200, 'Service is healthy')
    @scan_api.response(503, 'Service is unhealthy')
    def get(self):
        """Comprehensive health check endpoint"""
        # Get request ID
        request_id = request.headers.get('X-Request-ID', 'no-id')
        
        logger.info("Health check initiated", extra={
            'request_id': request_id
        })
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': 'HubSpot Extraction Service',
            'version': '2.0.0',
            'checks': {}
        }
        
        # Database health
        try:
            if check_db_connection():
                health_status['checks']['database'] = 'healthy'
                logger.info("Database health check: healthy", extra={
                    'request_id': request_id
                })
                
                try:
                    db_stats = get_db_stats()
                    health_status['checks']['database_pool'] = f"Pool: {db_stats.get('pool_size', 'unknown')}, Active: {db_stats.get('checked_out', 0)}, Available: {db_stats.get('checked_in', 0)}"
                except Exception:
                    health_status['checks']['database_pool'] = 'stats_unavailable'
            else:
                health_status['checks']['database'] = 'degraded'
                health_status['status'] = 'degraded'
                logger.warning("Database health check: degraded", extra={
                    'request_id': request_id
                })
        except Exception as e:
            health_status['checks']['database'] = f'degraded: {str(e)}'
            health_status['status'] = 'degraded'
            logger.error(f"Database health check error: {str(e)}", 
                        extra={'request_id': request_id},
                        exc_info=True)
        
        # Thread pool health
        try:
            thread_stats = extraction_service.get_thread_pool_stats()
            active_extractions = extraction_service.get_active_extractions_count()
            
            if thread_stats.get('shutdown', False):
                health_status['checks']['thread_pool'] = 'shutdown'
                health_status['status'] = 'unhealthy'
                logger.warning("Thread pool is shutdown", extra={
                    'request_id': request_id
                })
            else:
                health_status['checks']['thread_pool'] = f"Workers: {thread_stats.get('max_workers', 'unknown')}, Active: {thread_stats.get('active_threads', 0)}, Pending: {thread_stats.get('pending_tasks', 0)}"
                health_status['checks']['active_extractions'] = f'{active_extractions} running'
        except Exception as e:
            health_status['checks']['thread_pool'] = f'error: {str(e)}'
            logger.error(f"Thread pool check error: {str(e)}", 
                        extra={'request_id': request_id},
                        exc_info=True)
        
        # Add system stats
        try:
            from services.job_service import JobService
            job_service = JobService()
            job_stats = job_service.get_job_statistics()
            
            health_status['system_stats'] = {
                'total_extractions_today': job_stats.get('total_jobs', 0),
                'successful_extractions': job_stats.get('completed_jobs', 0),
                'failed_extractions': job_stats.get('failed_jobs', 0),
                'average_extraction_time': f"{job_stats.get('average_extraction_time', 0)} seconds" if job_stats.get('average_extraction_time') else 'N/A'
            }
        except Exception:
            health_status['system_stats'] = {'error': 'Stats unavailable'}
        
        # Log overall health status
        logger.info(f"Health check completed: {health_status['status']}", extra={
            'request_id': request_id, 
            'health_status': health_status['status']
        })
        
        status_code = 503 if health_status['status'] == 'unhealthy' else 200
        return health_status, status_code