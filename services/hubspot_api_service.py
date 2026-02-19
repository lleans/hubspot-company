import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from utils.decorators import retry_on_failure
from utils.exceptions import HubSpotAPIError
from config import get_config
from loki_logger import setup_loki_logging, get_logger

# Get a logger for this module
logger = get_logger(__name__)
config = get_config()

class HubSpotAPIService:
    """
    Service for HubSpot API communication with robust error handling and rate limiting
    """
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = config.HUBSPOT_API_BASE_URL
        self.timeout = config.HUBSPOT_API_TIMEOUT
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        self.rate_limit_delay = 0.1  # Default delay between requests
    
    def validate_token(self) -> bool:
        """
        Validate the HubSpot API token by making a test request
        
        Returns:
            bool: True if token is valid
        """
        try:
            url = f"{self.base_url}/crm/v3/objects/companies"
            params = {'limit': 1}
            response = requests.get(
                url, 
                headers=self.headers, 
                params=params, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info("HubSpot API token validation successful")
                return True
            elif response.status_code == 401:
                logger.error("HubSpot API token validation failed: Unauthorized")
                return False
            else:
                logger.warning(f"HubSpot API token validation returned status: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Token validation request failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            return False
    
    def _handle_rate_limiting(self, response):
        """Handle HubSpot API rate limiting"""
        if response.status_code == 429:
            # Check for Retry-After header
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                delay = int(retry_after)
                logger.warning(f"Rate limited by HubSpot. Waiting {delay} seconds...")
                time.sleep(delay)
            else:
                # Default backoff
                self.rate_limit_delay = min(self.rate_limit_delay * 2, 10)
                logger.warning(f"Rate limited. Backing off for {self.rate_limit_delay} seconds...")
                time.sleep(self.rate_limit_delay)
        else:
            # Reset rate limit delay on successful requests
            self.rate_limit_delay = 0.1
    
    @retry_on_failure(max_retries=3, delay=1, backoff=2)
    def _paginated_get(self, url: str, params: Dict = None) -> List[Dict]:
        """
        Make paginated GET requests to HubSpot API with comprehensive error handling
        
        Args:
            url: API endpoint URL
            params: Query parameters
            
        Returns:
            List of all results from paginated responses
            
        Raises:
            HubSpotAPIError: If API request fails after retries
        """
        results = []
        after = None
        params = params or {}
        page_count = 0
        
        logger.info(f"Starting paginated request to {url}")
        
        while True:
            page_count += 1
            if after:
                params['after'] = after
            
            logger.debug(f"Page {page_count}: Making request with params: {params}")
            
            try:
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params, 
                    timeout=self.timeout
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    self._handle_rate_limiting(response)
                    continue  # Retry the same request
                
                # Handle other errors
                if response.status_code != 200:
                    error_details = {}
                    try:
                        error_details = response.json()
                    except:
                        error_details = {'message': response.text}
                    
                    raise HubSpotAPIError(
                        f"HubSpot API error (Status {response.status_code}): {error_details.get('message', response.text)}",
                        status_code=response.status_code,
                        response=response
                    )
                
                # Parse successful response
                data = response.json()
                batch_results = data.get('results', [])
                results.extend(batch_results)
                
                logger.info(f"Page {page_count}: Retrieved {len(batch_results)} records, total: {len(results)}")
                
                # Check for pagination
                paging = data.get('paging', {})
                after = paging.get('next', {}).get('after')
                
                if not after:
                    logger.info(f"Pagination complete. Total pages: {page_count}, Total records: {len(results)}")
                    break
                
                # Respectful rate limiting
                time.sleep(self.rate_limit_delay)
                
            except requests.exceptions.Timeout:
                raise HubSpotAPIError(f"Request timeout after {self.timeout} seconds")
            except requests.exceptions.ConnectionError:
                raise HubSpotAPIError("Connection error - unable to reach HubSpot API")
            except requests.exceptions.RequestException as e:
                raise HubSpotAPIError(f"Request failed: {str(e)}")
            except Exception as e:
                raise HubSpotAPIError(f"Unexpected error during API request: {str(e)}")
        
        return results
    
    def get_companies(self, properties: List[str] = None) -> List[Dict]:
        """
        Fetch all company records from HubSpot
        
        Args:
            properties: List of properties to retrieve
            
        Returns:
            List of company records with standardized structure
        """
        url = config.HUBSPOT_COMPANY_URL
        
        # Use configured properties or defaults
        if not properties:
            properties = [prop.strip() for prop in config.COMPANY_PROPERTIES.split(',')]
        
        params = {
            'archived': 'false',
            'properties': ','.join(properties),
            'limit': 100  # Maximum allowed by HubSpot
        }
        
        logger.info("Starting company extraction from HubSpot")
        start_time = time.time()
        
        try:
            companies = self._paginated_get(url, params)
            
            # Standardize company data structure
            standardized_companies = []
            for company in companies:
                standardized_company = self._standardize_company_data(company)
                standardized_companies.append(standardized_company)
            
            duration = time.time() - start_time
            logger.info(f"Company extraction completed: {len(standardized_companies)} companies in {duration:.2f} seconds")
            
            return standardized_companies
            
        except Exception as e:
            logger.error(f"Company extraction failed: {str(e)}")
            raise
    
    def get_deals(self, properties: List[str] = None) -> List[Dict]:
        """
        Fetch all deal records from HubSpot
        
        Args:
            properties: List of properties to retrieve
            
        Returns:
            List of deal records with standardized structure
        """
        url = config.HUBSPOT_DEAL_URL
        
        # Use configured properties or defaults
        if not properties:
            properties = [prop.strip() for prop in config.DEAL_PROPERTIES.split(',')]
        
        params = {
            'archived': 'false',
            'properties': ','.join(properties),
            'limit': 100  # Maximum allowed by HubSpot
        }
        
        logger.info("Starting deal extraction from HubSpot")
        start_time = time.time()
        
        try:
            deals = self._paginated_get(url, params)
            
            # Standardize deal data structure
            standardized_deals = []
            for deal in deals:
                standardized_deal = self._standardize_deal_data(deal)
                standardized_deals.append(standardized_deal)
            
            duration = time.time() - start_time
            logger.info(f"Deal extraction completed: {len(standardized_deals)} deals in {duration:.2f} seconds")
            
            return standardized_deals
            
        except Exception as e:
            logger.error(f"Deal extraction failed: {str(e)}")
            raise
    
    def get_deals_for_company(self, company_id: str) -> List[Dict]:
        """
        Fetch deals associated with a specific company
        
        Args:
            company_id: HubSpot company ID
            
        Returns:
            List of associated deal records
        """
        url = f"{config.HUBSPOT_COMPANY_URL}/{company_id}/associations/deals"
        params = {'archived': 'false'}
        
        logger.debug(f"Fetching deals for company {company_id}")
        
        try:
            return self._paginated_get(url, params)
        except Exception as e:
            logger.warning(f"Failed to fetch deals for company {company_id}: {str(e)}")
            return []
    
    def get_deal_pipelines(self) -> List[Dict]:
        """
        Fetch all deal pipeline definitions with stages
        
        Returns:
            List of pipeline definitions with complete stage information
        """
        url = config.HUBSPOT_PIPELINE_URL
        
        logger.info("Starting pipeline extraction from HubSpot")
        start_time = time.time()
        
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code != 200:
                error_details = {}
                try:
                    error_details = response.json()
                except:
                    error_details = {'message': response.text}
                
                raise HubSpotAPIError(
                    f"HubSpot API error (Status {response.status_code}): {error_details.get('message', response.text)}",
                    status_code=response.status_code,
                    response=response
                )
            
            data = response.json()
            pipelines = data.get('results', [])
            
            # Standardize pipeline data
            standardized_pipelines = []
            for pipeline in pipelines:
                standardized_pipeline = self._standardize_pipeline_data(pipeline)
                standardized_pipelines.append(standardized_pipeline)
            
            duration = time.time() - start_time
            logger.info(f"Pipeline extraction completed: {len(standardized_pipelines)} pipelines in {duration:.2f} seconds")
            
            return standardized_pipelines
            
        except requests.exceptions.RequestException as e:
            raise HubSpotAPIError(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Pipeline extraction failed: {str(e)}")
            raise
    
    def _standardize_company_data(self, company_data: Dict) -> Dict:
        """Standardize company data structure"""
        properties = company_data.get('properties', {})
        
        # Parse dates safely
        created_date = self._parse_hubspot_date(properties.get('createdate'))
        updated_date = self._parse_hubspot_date(properties.get('hs_lastmodifieddate'))
        
        return {
            'id': company_data.get('id'),
            'properties': properties,
            'created_date': created_date,
            'updated_date': updated_date,
            'archived': company_data.get('archived', False)
        }
    
    def _standardize_deal_data(self, deal_data: Dict) -> Dict:
        """Standardize deal data structure"""
        properties = deal_data.get('properties', {})
        
        # Parse dates safely
        created_date = self._parse_hubspot_date(properties.get('createdate'))
        updated_date = self._parse_hubspot_date(properties.get('hs_lastmodifieddate'))
        close_date = self._parse_hubspot_date(properties.get('closedate'))
        
        return {
            'id': deal_data.get('id'),
            'properties': properties,
            'created_date': created_date,
            'updated_date': updated_date,
            'close_date': close_date,
            'archived': deal_data.get('archived', False)
        }
    
    def _standardize_pipeline_data(self, pipeline_data: Dict) -> Dict:
        """Standardize pipeline data structure"""
        created_date = self._parse_hubspot_date(pipeline_data.get('createdAt'))
        updated_date = self._parse_hubspot_date(pipeline_data.get('updatedAt'))
        
        return {
            'id': pipeline_data.get('id'),
            'label': pipeline_data.get('label'),
            'displayOrder': pipeline_data.get('displayOrder'),
            'active': pipeline_data.get('archived') is not True,
            'stages': pipeline_data.get('stages', []),
            'created_date': created_date,
            'updated_date': updated_date,
            'raw_data': pipeline_data
        }
    
    def _parse_hubspot_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse HubSpot date string to datetime object
        HubSpot typically returns dates as ISO format strings or timestamps
        """
        if not date_str:
            return None
        
        try:
            # Try parsing as timestamp (milliseconds)
            if date_str.isdigit():
                timestamp = int(date_str) / 1000  # Convert from milliseconds
                return datetime.fromtimestamp(timestamp)
            
            # Try parsing as ISO format
            if 'T' in date_str:
                # Handle various ISO formats
                date_str = date_str.replace('Z', '+00:00')
                if '+' not in date_str and date_str.endswith(':00'):
                    date_str = date_str[:-3] + '+00:00'
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            # Try parsing as date only
            return datetime.strptime(date_str, '%Y-%m-%d')
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Failed to parse date '{date_str}': {str(e)}")
            return None
        
    def get_deal_stage_history(self, deal_id: str) -> List[Dict]:
        """
        Fetch complete stage history/timeline for a specific deal
        
        Args:
            deal_id: HubSpot deal ID
            
        Returns:
            List of stage history records with timeline information
        """
        logger.info(f"Fetching stage history for deal {deal_id}")
        start_time = time.time()
        
        try:
            # Method 1: Try to get timeline events (if available)
            timeline_url = f"{self.base_url}/crm/v3/objects/deals/{deal_id}/timeline"
            
            try:
                timeline_response = requests.get(
                    timeline_url, 
                    headers=self.headers, 
                    timeout=self.timeout
                )
                
                if timeline_response.status_code == 200:
                    timeline_data = timeline_response.json()
                    stage_events = []
                    
                    # Filter for stage change events
                    for event in timeline_data.get('results', []):
                        if event.get('eventType') == 'PROPERTY_CHANGE' and \
                           event.get('propertyName') == 'dealstage':
                            stage_events.append({
                                'timestamp': event.get('timestamp'),
                                'stage_id': event.get('propertyValue'),
                                'previous_stage_id': event.get('previousValue'),
                                'source': event.get('sourceType'),
                                'user_id': event.get('userId'),
                                'raw_event': event
                            })
                    
                    if stage_events:
                        logger.info(f"Retrieved {len(stage_events)} stage events from timeline for deal {deal_id}")
                        duration = time.time() - start_time
                        logger.info(f"Stage history extraction completed in {duration:.2f} seconds")
                        return stage_events
                        
            except Exception as timeline_error:
                logger.debug(f"Timeline API not available for deal {deal_id}: {str(timeline_error)}")
            
            # Method 2: Get stage entry date properties (fallback)
            deal_url = f"{self.base_url}/crm/v3/objects/deals/{deal_id}"
            
            # Get all stage entry date properties
            stage_date_properties = [
                'hs_date_entered_appointmentscheduled',
                'hs_date_entered_qualifiedtobuy', 
                'hs_date_entered_presentationscheduled',
                'hs_date_entered_decisionmakerboughtin',
                'hs_date_entered_contractsent',
                'hs_date_entered_closedwon',
                'hs_date_entered_closedlost',
                'hs_date_entered_1',
                'hs_date_entered_2', 
                'hs_date_entered_3',
                'hs_date_entered_4',
                'hs_date_entered_5',
                'hs_date_entered_6',
                'hs_date_entered_7',
                'hs_date_entered_8',
                'hs_date_entered_9',
                'hs_date_entered_10'
            ]
            
            # Also get current deal properties
            deal_properties = [
                'dealstage', 'pipeline', 'createdate', 'hs_lastmodifieddate'
            ] + stage_date_properties
            
            params = {
                'properties': ','.join(deal_properties)
            }
            
            response = requests.get(deal_url, headers=self.headers, params=params, timeout=self.timeout)
            
            if response.status_code != 200:
                error_details = {}
                try:
                    error_details = response.json()
                except:
                    error_details = {'message': response.text}
                
                raise HubSpotAPIError(
                    f"HubSpot API error (Status {response.status_code}): {error_details.get('message', response.text)}",
                    status_code=response.status_code,
                    response=response
                )
            
            deal_data = response.json()
            properties = deal_data.get('properties', {})
            
            # Extract stage history from date properties
            stage_history = []
            
            for prop_name, prop_value in properties.items():
                if prop_name.startswith('hs_date_entered_') and prop_value:
                    stage_id = prop_name.replace('hs_date_entered_', '')
                    
                    # Parse the timestamp
                    entry_date = self._parse_hubspot_date(prop_value)
                    
                    if entry_date:
                        stage_history.append({
                            'stage_id': stage_id,
                            'entry_timestamp': int(entry_date.timestamp() * 1000),  # Convert to milliseconds
                            'entry_date': entry_date,
                            'property_name': prop_name,
                            'source': 'property_history'
                        })
            
            # Sort by entry date
            stage_history.sort(key=lambda x: x['entry_timestamp'])
            
            # Calculate durations
            for i in range(len(stage_history)):
                current_stage = stage_history[i]
                
                if i < len(stage_history) - 1:
                    # Duration until next stage
                    next_stage = stage_history[i + 1]
                    duration_ms = next_stage['entry_timestamp'] - current_stage['entry_timestamp']
                    current_stage['duration_days'] = duration_ms / (1000 * 60 * 60 * 24)
                    current_stage['duration_hours'] = duration_ms / (1000 * 60 * 60)
                    current_stage['is_current_stage'] = False
                else:
                    # Current stage - calculate duration from entry to now
                    current_time_ms = int(time.time() * 1000)
                    duration_ms = current_time_ms - current_stage['entry_timestamp']
                    current_stage['duration_days'] = duration_ms / (1000 * 60 * 60 * 24)
                    current_stage['duration_hours'] = duration_ms / (1000 * 60 * 60)
                    current_stage['is_current_stage'] = True
                
                # Add stage order
                current_stage['stage_order'] = i
            
            duration = time.time() - start_time
            logger.info(f"Stage history extraction completed: {len(stage_history)} stages for deal {deal_id} in {duration:.2f} seconds")
            
            return stage_history
            
        except requests.exceptions.RequestException as e:
            raise HubSpotAPIError(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Stage history extraction failed for deal {deal_id}: {str(e)}")
            raise
    
    def get_bulk_deal_stage_history(self, deal_ids: List[str]) -> Dict[str, List[Dict]]:
        """
        Fetch stage history for multiple deals efficiently
        
        Args:
            deal_ids: List of HubSpot deal IDs
            
        Returns:
            Dictionary mapping deal_id to list of stage history records
        """
        logger.info(f"Fetching stage history for {len(deal_ids)} deals")
        start_time = time.time()
        
        results = {}
        failed_deals = []
        
        for i, deal_id in enumerate(deal_ids, 1):
            try:
                logger.debug(f"Processing deal {i}/{len(deal_ids)}: {deal_id}")
                
                stage_history = self.get_deal_stage_history(deal_id)
                results[deal_id] = stage_history
                
                # Rate limiting between requests
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.warning(f"Failed to get stage history for deal {deal_id}: {str(e)}")
                failed_deals.append(deal_id)
                results[deal_id] = []
        
        duration = time.time() - start_time
        logger.info(f"Bulk stage history extraction completed: {len(results)} deals processed, {len(failed_deals)} failures in {duration:.2f} seconds")
        
        if failed_deals:
            logger.warning(f"Failed to process deals: {failed_deals}")
        
        return results
    
    def get_deal_stage_properties(self) -> List[str]:
        """
        Get all available stage entry date properties from HubSpot
        This is useful for understanding what stage history data is available
        
        Returns:
            List of stage entry date property names
        """
        try:
            # Get deal properties schema
            url = f"{self.base_url}/crm/v3/properties/deals"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code != 200:
                logger.warning(f"Could not fetch deal properties schema: {response.status_code}")
                return []
            
            properties_data = response.json()
            stage_properties = []
            
            for prop in properties_data.get('results', []):
                prop_name = prop.get('name', '')
                if prop_name.startswith('hs_date_entered_'):
                    stage_properties.append(prop_name)
            
            logger.info(f"Found {len(stage_properties)} stage entry date properties")
            return stage_properties
            
        except Exception as e:
            logger.error(f"Failed to get stage properties: {str(e)}")
            return []
    
    def analyze_deal_velocity(self, deal_id: str) -> Dict:
        """
        Analyze velocity metrics for a specific deal
        
        Args:
            deal_id: HubSpot deal ID
            
        Returns:
            Dictionary with velocity analysis
        """
        try:
            stage_history = self.get_deal_stage_history(deal_id)
            
            if not stage_history:
                return {'error': 'No stage history available'}
            
            # Calculate total cycle time
            total_duration_days = sum(stage.get('duration_days', 0) for stage in stage_history if not stage.get('is_current_stage'))
            
            # Find longest stage
            longest_stage = max(stage_history, key=lambda x: x.get('duration_days', 0), default=None)
            
            # Count stage transitions
            total_stages = len(stage_history)
            
            # Calculate average time per stage
            avg_time_per_stage = total_duration_days / max(total_stages - 1, 1) if total_stages > 1 else 0
            
            return {
                'deal_id': deal_id,
                'total_stages': total_stages,
                'total_cycle_time_days': total_duration_days,
                'avg_time_per_stage_days': avg_time_per_stage,
                'longest_stage': {
                    'stage_id': longest_stage.get('stage_id') if longest_stage else None,
                    'duration_days': longest_stage.get('duration_days', 0) if longest_stage else 0
                },
                'current_stage_id': next((s['stage_id'] for s in stage_history if s.get('is_current_stage')), None),
                'velocity_score': total_duration_days / max(total_stages, 1),  # Lower is better
                'stage_breakdown': [
                    {
                        'stage_id': stage['stage_id'],
                        'duration_days': stage.get('duration_days', 0),
                        'percentage_of_total': (stage.get('duration_days', 0) / max(total_duration_days, 1)) * 100
                    }
                    for stage in stage_history if not stage.get('is_current_stage')
                ]
            }
            
        except Exception as e:
            logger.error(f"Velocity analysis failed for deal {deal_id}: {str(e)}")
            return {'error': str(e)}
