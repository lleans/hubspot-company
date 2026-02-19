#!/usr/bin/env python3
"""
Comprehensive HubSpot API Permission Tester
Tests all HubSpot API scopes and permissions with detailed analysis
"""

import requests
import json
from typing import Dict, List, Optional, Tuple
import os
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import concurrent.futures
import threading

class PermissionLevel(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

class TestCategory(Enum):
    CRITICAL = "critical"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"
    ADVANCED = "advanced"

@dataclass
class EndpointTest:
    name: str
    url: str
    method: str = "GET"
    params: dict = None
    body: dict = None
    required_scopes: List[str] = None
    category: TestCategory = TestCategory.OPTIONAL
    description: str = ""
    permission_level: PermissionLevel = PermissionLevel.READ
    depends_on: List[str] = None
    test_data_required: bool = False

class ComprehensiveHubSpotTester:
    def __init__(self, api_token: str, portal_id: str = None):
        self.api_token = api_token
        self.portal_id = portal_id
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        self.rate_limit_delay = 0.1
        self.test_results = {}
        self.lock = threading.Lock()
        
    def get_all_test_endpoints(self) -> List[EndpointTest]:
        """Define comprehensive list of HubSpot API endpoints to test"""
        
        endpoints = [
            # ================================
            # AUTHENTICATION & TOKEN INFO
            # ================================
            EndpointTest(
                name="token_info",
                url=f"{self.base_url}/oauth/v1/access-tokens/{self.api_token}",
                required_scopes=["oauth"],
                category=TestCategory.CRITICAL,
                description="Validate token and get scope information"
            ),
            
            # ================================
            # CRM OBJECTS - CONTACTS
            # ================================
            EndpointTest(
                name="contacts_read",
                url=f"{self.base_url}/crm/v3/objects/contacts",
                params={"limit": 1},
                required_scopes=["crm.objects.contacts.read"],
                category=TestCategory.RECOMMENDED,
                description="Read contact records"
            ),
            EndpointTest(
                name="contacts_write",
                url=f"{self.base_url}/crm/v3/objects/contacts",
                method="POST",
                body={"properties": {"email": f"test-{int(time.time())}@example.com", "firstname": "Test"}},
                required_scopes=["crm.objects.contacts.write"],
                category=TestCategory.OPTIONAL,
                description="Create contact records",
                permission_level=PermissionLevel.WRITE
            ),
            EndpointTest(
                name="contacts_search", 
                url=f"{self.base_url}/crm/v3/objects/contacts/search",
                method="POST",
                body={"limit": 1, "properties": ["email", "firstname"]},
                required_scopes=["crm.objects.contacts.read"],
                category=TestCategory.RECOMMENDED,
                description="Search contact records"
            ),
            
            # ================================
            # CRM OBJECTS - COMPANIES
            # ================================
            EndpointTest(
                name="companies_read",
                url=f"{self.base_url}/crm/v3/objects/companies",
                params={"limit": 1},
                required_scopes=["crm.objects.companies.read"],
                category=TestCategory.CRITICAL,
                description="Read company records"
            ),
            EndpointTest(
                name="companies_write",
                url=f"{self.base_url}/crm/v3/objects/companies",
                method="POST", 
                body={"properties": {"name": f"Test Company {int(time.time())}", "domain": "test.example"}},
                required_scopes=["crm.objects.companies.write"],
                category=TestCategory.OPTIONAL,
                description="Create company records",
                permission_level=PermissionLevel.WRITE
            ),
            EndpointTest(
                name="companies_search",
                url=f"{self.base_url}/crm/v3/objects/companies/search",
                method="POST",
                body={"limit": 1, "properties": ["name", "domain"]},
                required_scopes=["crm.objects.companies.read"],
                category=TestCategory.CRITICAL,
                description="Search company records"
            ),
            
            # ================================
            # CRM OBJECTS - DEALS
            # ================================
            EndpointTest(
                name="deals_read",
                url=f"{self.base_url}/crm/v3/objects/deals",
                params={"limit": 1},
                required_scopes=["crm.objects.deals.read"],
                category=TestCategory.CRITICAL,
                description="Read deal records"
            ),
            EndpointTest(
                name="deals_write",
                url=f"{self.base_url}/crm/v3/objects/deals",
                method="POST",
                body={"properties": {"dealname": f"Test Deal {int(time.time())}", "amount": "1000"}},
                required_scopes=["crm.objects.deals.write"],
                category=TestCategory.OPTIONAL,
                description="Create deal records",
                permission_level=PermissionLevel.WRITE
            ),
            EndpointTest(
                name="deals_search",
                url=f"{self.base_url}/crm/v3/objects/deals/search",
                method="POST", 
                body={"limit": 1, "properties": ["dealname", "amount"]},
                required_scopes=["crm.objects.deals.read"],
                category=TestCategory.CRITICAL,
                description="Search deal records"
            ),
            
            # ================================
            # CRM OBJECTS - TICKETS
            # ================================
            EndpointTest(
                name="tickets_read",
                url=f"{self.base_url}/crm/v3/objects/tickets",
                params={"limit": 1},
                required_scopes=["tickets"],
                category=TestCategory.OPTIONAL,
                description="Read ticket records"
            ),
            EndpointTest(
                name="tickets_write",
                url=f"{self.base_url}/crm/v3/objects/tickets",
                method="POST",
                body={"properties": {"subject": f"Test Ticket {int(time.time())}", "content": "Test content"}},
                required_scopes=["tickets"],
                category=TestCategory.OPTIONAL,
                description="Create ticket records",
                permission_level=PermissionLevel.WRITE
            ),
            
            # ================================
            # CRM OBJECTS - PRODUCTS
            # ================================
            EndpointTest(
                name="products_read",
                url=f"{self.base_url}/crm/v3/objects/products",
                params={"limit": 1},
                required_scopes=["e-commerce"],
                category=TestCategory.OPTIONAL,
                description="Read product records"
            ),
            
            # ================================
            # CRM OBJECTS - LINE ITEMS
            # ================================
            EndpointTest(
                name="line_items_read",
                url=f"{self.base_url}/crm/v3/objects/line_items",
                params={"limit": 1},
                required_scopes=["e-commerce"],
                category=TestCategory.OPTIONAL,
                description="Read line item records"
            ),
            
            # ================================
            # CRM OBJECTS - QUOTES
            # ================================
            EndpointTest(
                name="quotes_read",
                url=f"{self.base_url}/crm/v3/objects/quotes",
                params={"limit": 1},
                required_scopes=["e-commerce"],
                category=TestCategory.OPTIONAL,
                description="Read quote records"
            ),
            
            # ================================
            # CRM SCHEMAS & PROPERTIES
            # ================================
            EndpointTest(
                name="deal_pipelines",
                url=f"{self.base_url}/crm/v3/pipelines/deals",
                required_scopes=["crm.schemas.deals.read"],
                category=TestCategory.CRITICAL,
                description="Read deal pipelines and stages"
            ),
            EndpointTest(
                name="ticket_pipelines",
                url=f"{self.base_url}/crm/v3/pipelines/tickets",
                required_scopes=["crm.schemas.deals.read"],
                category=TestCategory.OPTIONAL,
                description="Read ticket pipelines"
            ),
            EndpointTest(
                name="contact_properties",
                url=f"{self.base_url}/crm/v3/properties/contacts",
                required_scopes=["crm.schemas.contacts.read"],
                category=TestCategory.RECOMMENDED,
                description="Read contact properties schema"
            ),
            EndpointTest(
                name="company_properties",
                url=f"{self.base_url}/crm/v3/properties/companies",
                required_scopes=["crm.schemas.companies.read"],
                category=TestCategory.RECOMMENDED,
                description="Read company properties schema"
            ),
            EndpointTest(
                name="deal_properties",
                url=f"{self.base_url}/crm/v3/properties/deals",
                required_scopes=["crm.schemas.deals.read"],
                category=TestCategory.RECOMMENDED,
                description="Read deal properties schema"
            ),
            
            # ================================
            # CRM ASSOCIATIONS
            # ================================
            EndpointTest(
                name="associations_schema",
                url=f"{self.base_url}/crm/v4/associations/contact/company/labels",
                required_scopes=["crm.objects.contacts.read", "crm.objects.companies.read"],
                category=TestCategory.RECOMMENDED,
                description="Read association schemas"
            ),
            
            # ================================
            # COMMUNICATION & ENGAGEMENT
            # ================================
            EndpointTest(
                name="communications_read",
                url=f"{self.base_url}/communications/v3/communications/timeline",
                params={"limit": 1},
                required_scopes=["communication_preferences.read"],
                category=TestCategory.OPTIONAL,
                description="Read communication timeline"
            ),
            EndpointTest(
                name="calls_read",
                url=f"{self.base_url}/crm/v3/objects/calls",
                params={"limit": 1},
                required_scopes=["crm.objects.contacts.read"],
                category=TestCategory.OPTIONAL,
                description="Read call records"
            ),
            EndpointTest(
                name="emails_read",
                url=f"{self.base_url}/crm/v3/objects/emails",
                params={"limit": 1},
                required_scopes=["crm.objects.contacts.read"],
                category=TestCategory.OPTIONAL,
                description="Read email records"
            ),
            EndpointTest(
                name="meetings_read",
                url=f"{self.base_url}/crm/v3/objects/meetings",
                params={"limit": 1},
                required_scopes=["crm.objects.contacts.read"],
                category=TestCategory.OPTIONAL,
                description="Read meeting records"
            ),
            EndpointTest(
                name="notes_read",
                url=f"{self.base_url}/crm/v3/objects/notes",
                params={"limit": 1},
                required_scopes=["crm.objects.contacts.read"],
                category=TestCategory.OPTIONAL,
                description="Read note records"
            ),
            EndpointTest(
                name="tasks_read",
                url=f"{self.base_url}/crm/v3/objects/tasks",
                params={"limit": 1},
                required_scopes=["crm.objects.contacts.read"],
                category=TestCategory.OPTIONAL,
                description="Read task records"
            ),
            
            # ================================
            # MARKETING & AUTOMATION
            # ================================
            EndpointTest(
                name="lists_read",
                url=f"{self.base_url}/contacts/v1/lists",
                required_scopes=["crm.lists.read"],
                category=TestCategory.OPTIONAL,
                description="Read contact lists"
            ),
            EndpointTest(
                name="workflows_read",
                url=f"{self.base_url}/automation/v3/workflows",
                required_scopes=["automation"],
                category=TestCategory.ADVANCED,
                description="Read workflows"
            ),
            EndpointTest(
                name="forms_read",
                url=f"{self.base_url}/forms/v2/forms",
                required_scopes=["forms"],
                category=TestCategory.OPTIONAL,
                description="Read forms"
            ),
            
            # ================================
            # CONTENT & CMS
            # ================================
            EndpointTest(
                name="blog_posts_read",
                url=f"{self.base_url}/content/api/v2/blog-posts",
                required_scopes=["content"],
                category=TestCategory.OPTIONAL,
                description="Read blog posts"
            ),
            EndpointTest(
                name="pages_read",
                url=f"{self.base_url}/content/api/v2/pages",
                required_scopes=["content"],
                category=TestCategory.OPTIONAL,
                description="Read landing pages"
            ),
            EndpointTest(
                name="files_read",
                url=f"{self.base_url}/files/v3/files",
                params={"limit": 1},
                required_scopes=["files"],
                category=TestCategory.OPTIONAL,
                description="Read file manager files"
            ),
            
            # ================================
            # ANALYTICS & REPORTING
            # ================================
            EndpointTest(
                name="analytics_views",
                url=f"{self.base_url}/analytics/v2/reports",
                required_scopes=["reports"],
                category=TestCategory.ADVANCED,
                description="Read analytics reports"
            ),
            
            # ================================
            # SETTINGS & ACCOUNT
            # ================================
            EndpointTest(
                name="account_info",
                url=f"{self.base_url}/account-info/v3/details",
                required_scopes=["account-info.security.read"],
                category=TestCategory.ADVANCED,
                description="Read account information"
            ),
            EndpointTest(
                name="users_read",
                url=f"{self.base_url}/settings/v3/users",
                required_scopes=["settings.users.read"],
                category=TestCategory.ADVANCED,
                description="Read user information"
            ),
            EndpointTest(
                name="teams_read",
                url=f"{self.base_url}/settings/v3/users/teams",
                required_scopes=["settings.users.teams.read"],
                category=TestCategory.ADVANCED,
                description="Read team information"
            ),
            
            # ================================
            # INTEGRATIONS
            # ================================
            EndpointTest(
                name="timeline_events",
                url=f"{self.base_url}/integrations/v1/timeline/event-types",
                required_scopes=["timeline"],
                category=TestCategory.ADVANCED,
                description="Read timeline event types"
            ),
            
            # ================================
            # WEBHOOKS
            # ================================
            EndpointTest(
                name="webhooks_read",
                url=f"{self.base_url}/webhooks/v3/subscriptions",
                required_scopes=["webhooks"],
                category=TestCategory.ADVANCED,
                description="Read webhook subscriptions"
            ),
        ]
        
        return endpoints
    
    def test_endpoint(self, endpoint: EndpointTest) -> Dict:
        """Test a single endpoint"""
        
        start_time = time.time()
        result = {
            'name': endpoint.name,
            'url': endpoint.url,
            'method': endpoint.method,
            'category': endpoint.category.value,
            'description': endpoint.description,
            'required_scopes': endpoint.required_scopes or [],
            'permission_level': endpoint.permission_level.value,
            'test_time': None,
            'accessible': False,
            'status_code': None,
            'status': 'UNKNOWN',
            'error': None,
            'response_data': None,
            'recommendations': []
        }
        
        try:
            # Prepare request
            kwargs = {
                'headers': self.headers,
                'timeout': 10
            }
            
            if endpoint.params:
                kwargs['params'] = endpoint.params
            
            if endpoint.body and endpoint.method in ['POST', 'PUT', 'PATCH']:
                kwargs['json'] = endpoint.body
            
            # Make request
            response = requests.request(endpoint.method, endpoint.url, **kwargs)
            
            result['status_code'] = response.status_code
            result['test_time'] = round(time.time() - start_time, 3)
            
            # Analyze response
            if response.status_code == 200:
                result['accessible'] = True
                result['status'] = 'SUCCESS'
                
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        if 'results' in data:
                            result['response_data'] = {
                                'total_results': len(data.get('results', [])),
                                'has_more': data.get('paging', {}).get('next') is not None,
                                'sample_fields': list(data.get('results', [{}])[0].keys()) if data.get('results') else []
                            }
                        else:
                            result['response_data'] = {
                                'response_type': 'object',
                                'keys': list(data.keys())[:10]  # First 10 keys
                            }
                    elif isinstance(data, list):
                        result['response_data'] = {
                            'response_type': 'array',
                            'length': len(data),
                            'sample_fields': list(data[0].keys()) if data else []
                        }
                except:
                    result['response_data'] = {'response_type': 'non_json'}
                    
            elif response.status_code == 201:
                result['accessible'] = True
                result['status'] = 'CREATED'
                result['recommendations'].append("Write operation successful - consider cleanup")
                
            elif response.status_code == 401:
                result['status'] = 'UNAUTHORIZED'
                result['error'] = 'Invalid token or authentication failed'
                
            elif response.status_code == 403:
                result['status'] = 'FORBIDDEN'
                result['error'] = 'Insufficient permissions'
                
                if endpoint.required_scopes:
                    result['recommendations'].append(f"Add scopes: {', '.join(endpoint.required_scopes)}")
                    
            elif response.status_code == 404:
                result['status'] = 'NOT_FOUND'
                result['error'] = 'Endpoint not found or no data available'
                
            elif response.status_code == 429:
                result['status'] = 'RATE_LIMITED'
                result['error'] = 'Rate limit exceeded'
                result['accessible'] = True  # Token is valid, just rate limited
                result['recommendations'].append("Implement rate limiting in your application")
                
            elif response.status_code >= 500:
                result['status'] = 'SERVER_ERROR'
                result['error'] = f'Server error: {response.status_code}'
                
            else:
                result['status'] = f'HTTP_{response.status_code}'
                result['error'] = f'Unexpected status code: {response.status_code}'
            
            # Add response details for debugging
            try:
                error_data = response.json()
                if 'message' in error_data:
                    result['error'] = error_data['message']
                if 'category' in error_data:
                    result['error_category'] = error_data['category']
            except:
                pass
                
        except requests.exceptions.Timeout:
            result['status'] = 'TIMEOUT'
            result['error'] = 'Request timeout (>10s)'
            result['test_time'] = 10.0
            
        except requests.exceptions.ConnectionError:
            result['status'] = 'CONNECTION_ERROR'
            result['error'] = 'Failed to connect to HubSpot API'
            
        except Exception as e:
            result['status'] = 'EXCEPTION'
            result['error'] = str(e)
            result['test_time'] = round(time.time() - start_time, 3)
        
        # Rate limiting
        time.sleep(self.rate_limit_delay)
        
        return result
    
    def test_all_endpoints(self, max_workers: int = 5, categories: List[TestCategory] = None) -> Dict:
        """Test all endpoints with optional filtering and concurrency"""
        
        endpoints = self.get_all_test_endpoints()
        
        # Filter by categories if specified
        if categories:
            endpoints = [ep for ep in endpoints if ep.category in categories]
        
        print(f"🚀 Starting comprehensive HubSpot API test...")
        print(f"📊 Testing {len(endpoints)} endpoints across {len(set(ep.category for ep in endpoints))} categories")
        print(f"⚡ Using {max_workers} concurrent workers")
        print("=" * 80)
        
        results = {
            'summary': {},
            'token_info': {},
            'endpoints': {},
            'categories': {},
            'scopes_analysis': {},
            'recommendations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Test token info first
        token_endpoint = next((ep for ep in endpoints if ep.name == 'token_info'), None)
        if token_endpoint:
            print("\n🔍 Testing token information...")
            token_result = self.test_endpoint(token_endpoint)
            results['token_info'] = token_result
            
            if token_result['accessible']:
                try:
                    # Extract scopes from token info
                    response = requests.get(token_endpoint.url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        token_data = response.json()
                        results['token_info']['scopes'] = token_data.get('scopes', [])
                        results['token_info']['hub_domain'] = token_data.get('hub_domain')
                        results['token_info']['app_id'] = token_data.get('app_id')
                        
                        print(f"✅ Token valid - {len(token_data.get('scopes', []))} scopes detected")
                    else:
                        print(f"⚠️  Token info request failed: {response.status_code}")
                except Exception as e:
                    print(f"⚠️  Could not extract token details: {str(e)}")
            else:
                print(f"❌ Token validation failed: {token_result.get('error', 'Unknown error')}")
        
        # Remove token_info from main test list to avoid duplication
        endpoints = [ep for ep in endpoints if ep.name != 'token_info']
        
        print(f"\n🧪 Testing {len(endpoints)} API endpoints...")
        print("-" * 50)
        
        # Test endpoints concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_endpoint = {executor.submit(self.test_endpoint, ep): ep for ep in endpoints}
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_endpoint):
                endpoint = future_to_endpoint[future]
                try:
                    result = future.result()
                    results['endpoints'][endpoint.name] = result
                    
                    completed += 1
                    status_emoji = "✅" if result['accessible'] else "❌"
                    print(f"{status_emoji} [{completed:3d}/{len(endpoints)}] {endpoint.name:<20} - {result['status']}")
                    
                except Exception as e:
                    print(f"❌ [{completed:3d}/{len(endpoints)}] {endpoint.name:<20} - EXCEPTION: {str(e)}")
        
        # Analyze results
        self._analyze_results(results)
        
        return results
    
    def _analyze_results(self, results: Dict):
        """Analyze test results and generate insights"""
        
        endpoints = results['endpoints']
        token_scopes = results.get('token_info', {}).get('scopes', [])
        
        # Basic statistics
        total_endpoints = len(endpoints)
        accessible_endpoints = sum(1 for r in endpoints.values() if r['accessible'])
        
        # Category analysis
        categories = {}
        for result in endpoints.values():
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'accessible': 0, 'endpoints': []}
            
            categories[cat]['total'] += 1
            categories[cat]['endpoints'].append(result['name'])
            if result['accessible']:
                categories[cat]['accessible'] += 1
        
        # Status analysis
        status_counts = {}
        for result in endpoints.values():
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Scope analysis
        required_scopes = set()
        missing_scopes = set()
        
        for result in endpoints.values():
            for scope in result.get('required_scopes', []):
                required_scopes.add(scope)
                if not result['accessible'] and result['status'] == 'FORBIDDEN':
                    missing_scopes.add(scope)
        
        available_scopes = set(token_scopes)
        
        # Generate recommendations
        recommendations = []
        
        # Critical endpoints analysis
        critical_failed = [r for r in endpoints.values() 
                         if r['category'] == 'critical' and not r['accessible']]
        
        if critical_failed:
            recommendations.append({
                'type': 'critical',
                'message': f"Critical functionality missing: {len(critical_failed)} essential endpoints failed",
                'details': [f"{r['name']}: {r['error']}" for r in critical_failed]
            })
        
        # Missing scopes recommendations
        if missing_scopes:
            recommendations.append({
                'type': 'scopes',
                'message': f"Add {len(missing_scopes)} missing scopes to enable more functionality",
                'details': list(missing_scopes)
            })
        
        # Performance recommendations
        slow_endpoints = [r for r in endpoints.values() 
                         if r.get('test_time', 0) > 3.0]
        
        if slow_endpoints:
            recommendations.append({
                'type': 'performance',
                'message': f"{len(slow_endpoints)} endpoints are slow (>3s response time)",
                'details': [f"{r['name']}: {r['test_time']}s" for r in slow_endpoints]
            })
        
        # Update results
        results['summary'] = {
            'total_endpoints': total_endpoints,
            'accessible_endpoints': accessible_endpoints,
            'success_rate': round(accessible_endpoints / total_endpoints * 100, 1) if total_endpoints > 0 else 0,
            'status_breakdown': status_counts,
            'ready_for_production': accessible_endpoints >= total_endpoints * 0.7
        }
        
        results['categories'] = categories
        
        results['scopes_analysis'] = {
            'token_scopes': list(available_scopes),
            'required_scopes': list(required_scopes),
            'missing_scopes': list(missing_scopes),
            'scope_coverage': round(len(available_scopes & required_scopes) / len(required_scopes) * 100, 1) if required_scopes else 100
        }
        
        results['recommendations'] = recommendations
    
    def print_comprehensive_report(self, results: Dict):
        """Print a detailed, well-formatted report"""
        
        print(f"\n" + "="*80)
        print(f"🎯 COMPREHENSIVE HUBSPOT API PERMISSION REPORT")
        print(f"="*80)
        
        # Token Information
        if results.get('token_info'):
            token_info = results['token_info']
            print(f"\n📋 TOKEN INFORMATION:")
            print(f"   Status: {'✅ Valid' if token_info['accessible'] else '❌ Invalid'}")
            
            if token_info['accessible']:
                print(f"   Hub Domain: {token_info.get('hub_domain', 'Unknown')}")
                print(f"   App ID: {token_info.get('app_id', 'Unknown')}")
                print(f"   Scopes: {len(token_info.get('scopes', []))}")
                
                # Show first 10 scopes
                scopes = token_info.get('scopes', [])
                if scopes:
                    print(f"   Sample Scopes: {', '.join(scopes[:5])}{'...' if len(scopes) > 5 else ''}")
        
        # Summary Statistics
        summary = results['summary']
        print(f"\n📊 SUMMARY STATISTICS:")
        print(f"   Total Endpoints Tested: {summary['total_endpoints']}")
        print(f"   Accessible Endpoints: {summary['accessible_endpoints']}")
        print(f"   Success Rate: {summary['success_rate']}%")
        print(f"   Production Ready: {'✅ Yes' if summary['ready_for_production'] else '❌ No'}")
        
        # Category Breakdown
        print(f"\n📂 CATEGORY BREAKDOWN:")
        categories = results['categories']
        for category, data in categories.items():
            success_rate = round(data['accessible'] / data['total'] * 100, 1) if data['total'] > 0 else 0
            status_emoji = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"
            print(f"   {status_emoji} {category.upper():<12}: {data['accessible']}/{data['total']} ({success_rate}%)")
        
        # Status Breakdown
        print(f"\n📈 STATUS BREAKDOWN:")
        for status, count in sorted(results['summary']['status_breakdown'].items()):
            emoji = {
                'SUCCESS': '✅', 'CREATED': '✅', 'FORBIDDEN': '❌', 
                'UNAUTHORIZED': '❌', 'NOT_FOUND': '⚠️', 'RATE_LIMITED': '⚡',
                'TIMEOUT': '⏰', 'SERVER_ERROR': '🔥'
            }.get(status, '❓')
            print(f"   {emoji} {status:<15}: {count}")
        
        # Scope Analysis
        scope_analysis = results['scopes_analysis']
        print(f"\n🔒 SCOPE ANALYSIS:")
        print(f"   Available Scopes: {len(scope_analysis['token_scopes'])}")
        print(f"   Required Scopes: {len(scope_analysis['required_scopes'])}")
        print(f"   Missing Scopes: {len(scope_analysis['missing_scopes'])}")
        print(f"   Coverage: {scope_analysis['scope_coverage']}%")
        
        if scope_analysis['missing_scopes']:
            print(f"\n   Missing Scopes:")
            for scope in sorted(scope_analysis['missing_scopes'])[:10]:
                print(f"     • {scope}")
            if len(scope_analysis['missing_scopes']) > 10:
                print(f"     ... and {len(scope_analysis['missing_scopes']) - 10} more")
        
        # Critical Issues
        critical_issues = [r for r in results['endpoints'].values() 
                          if r['category'] == 'critical' and not r['accessible']]
        
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in critical_issues:
                print(f"   ❌ {issue['name']}: {issue['error']}")
                if issue.get('required_scopes'):
                    print(f"      Required: {', '.join(issue['required_scopes'])}")
        
        # Recommendations
        recommendations = results['recommendations']
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec['message']}")
                if isinstance(rec['details'], list):
                    for detail in rec['details'][:3]:
                        print(f"      • {detail}")
                    if len(rec['details']) > 3:
                        print(f"      ... and {len(rec['details']) - 3} more")
        
        # Next Steps
        print(f"\n🎯 NEXT STEPS:")
        if summary['ready_for_production']:
            print(f"   ✅ Your token is ready for production use!")
            print(f"   ✅ Most critical functionality is accessible")
            if scope_analysis['missing_scopes']:
                print(f"   📈 Consider adding {len(scope_analysis['missing_scopes'])} additional scopes for enhanced functionality")
        else:
            print(f"   ❌ Token needs additional configuration before production use")
            print(f"   🔧 Focus on resolving critical issues first")
            if scope_analysis['missing_scopes']:
                print(f"   🔑 Add missing scopes to unlock blocked functionality")
        
        print(f"\n" + "="*80)
    
    def export_detailed_report(self, results: Dict, filename: str = None):
        """Export comprehensive results with recommendations"""
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hubspot_comprehensive_test_{timestamp}.json"
        
        # Add metadata
        results['test_metadata'] = {
            'test_version': '2.0',
            'total_test_time': sum(r.get('test_time', 0) for r in results['endpoints'].values()),
            'test_categories': list(set(r['category'] for r in results['endpoints'].values())),
            'hubspot_api_version': 'v3',
            'tester_config': {
                'rate_limit_delay': self.rate_limit_delay,
                'timeout': 10
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Comprehensive report exported to: {filename}")
        return filename
    
    def test_specific_categories(self, categories: List[str]) -> Dict:
        """Test only specific categories of endpoints"""
        
        category_map = {cat.value: cat for cat in TestCategory}
        test_categories = [category_map[cat] for cat in categories if cat in category_map]
        
        return self.test_all_endpoints(categories=test_categories)
    
    def test_extraction_readiness(self) -> Dict:
        """Quick test specifically for data extraction readiness"""
        
        extraction_endpoints = [
            'token_info', 'companies_read', 'companies_search', 
            'deals_read', 'deals_search', 'deal_pipelines',
            'contacts_read', 'contact_properties', 'company_properties', 'deal_properties'
        ]
        
        endpoints = [ep for ep in self.get_all_test_endpoints() if ep.name in extraction_endpoints]
        
        print(f"🎯 Testing Data Extraction Readiness ({len(endpoints)} key endpoints)")
        print("="*60)
        
        results = {'endpoints': {}, 'extraction_ready': False}
        
        for endpoint in endpoints:
            result = self.test_endpoint(endpoint)
            results['endpoints'][endpoint.name] = result
            
            status_emoji = "✅" if result['accessible'] else "❌"
            print(f"{status_emoji} {endpoint.name:<20} - {result['status']}")
        
        # Check extraction readiness
        critical_endpoints = ['companies_read', 'deals_read', 'deal_pipelines']
        extraction_ready = all(
            results['endpoints'].get(ep, {}).get('accessible', False) 
            for ep in critical_endpoints
        )
        
        results['extraction_ready'] = extraction_ready
        
        print(f"\n🎯 Extraction Readiness: {'✅ READY' if extraction_ready else '❌ NOT READY'}")
        
        if not extraction_ready:
            failed = [ep for ep in critical_endpoints 
                     if not results['endpoints'].get(ep, {}).get('accessible', False)]
            print(f"   Missing: {', '.join(failed)}")
        
        return results

def main():
    """Interactive main function"""
    
    print("🎯 Comprehensive HubSpot API Permission Tester v2.0")
    print("="*60)
    
    # Get API token
    api_token = "pat-na2-9a92dd2d-66bf-46f2-abe0-2b862368c823"
    if not api_token:
        api_token = input("Enter your HubSpot API token: ").strip()
    
    if not api_token:
        print("❌ No API token provided. Exiting.")
        return
    
    # Initialize tester
    tester = ComprehensiveHubSpotTester(api_token)
    
    # Test options
    print(f"\n🔍 Test Options:")
    print(f"1. Quick extraction readiness test (recommended)")
    print(f"2. Test critical endpoints only")
    print(f"3. Comprehensive test (all endpoints)")
    print(f"4. Test specific categories")
    
    choice = input(f"\nSelect option (1-4): ").strip()
    
    if choice == '1':
        results = tester.test_extraction_readiness()
    elif choice == '2':
        results = tester.test_specific_categories(['critical'])
    elif choice == '3':
        results = tester.test_all_endpoints()
    elif choice == '4':
        print(f"\nAvailable categories: critical, recommended, optional, advanced")
        categories = input("Enter categories (comma-separated): ").strip().split(',')
        categories = [cat.strip() for cat in categories]
        results = tester.test_specific_categories(categories)
    else:
        print("Invalid choice. Running extraction readiness test...")
        results = tester.test_extraction_readiness()
    
    # Print report
    if 'summary' in results:  # Full test results
        tester.print_comprehensive_report(results)
        
        # Export option
        export = input(f"\n💾 Export detailed report? (y/n): ").lower()
        if export == 'y':
            tester.export_detailed_report(results)
    
    print(f"\n✨ Test completed! Thank you for using the HubSpot API Tester.")

if __name__ == "__main__":
    main()