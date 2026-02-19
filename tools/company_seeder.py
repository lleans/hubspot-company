#!/usr/bin/env python3
"""
HubSpot CRM Data Seeder
Quick script to create fake companies, pipelines, and deals with multiple stages
"""

import requests
import os
import time
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

class HubSpotSeeder:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        # Verify token by making a simple API call
        try:
            response = requests.get(f"{self.base_url}/crm/v3/objects/companies", 
                                  headers=self.headers, params={"limit": 1}, timeout=10)
            if response.status_code == 401:
                raise ValueError("Invalid API token")
            elif response.status_code == 403:
                raise ValueError("API token lacks required scopes")
            elif response.status_code not in [200, 429]:
                raise ValueError(f"Token verification failed: {response.status_code}")
            print("✅ Token verified")
        except requests.RequestException:
            raise ValueError("Failed to connect to HubSpot API")
    
    def _request(self, method, endpoint, data=None):
        """Make API request with rate limiting"""
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data, timeout=30)
        
        if response.status_code == 429:
            time.sleep(2)
            return self._request(method, endpoint, data)
        
        if response.status_code >= 400:
            error = response.json().get('message', response.text)
            raise Exception(f"API Error {response.status_code}: {error}")
        
        time.sleep(0.1)  # Rate limiting
        return response.json()
    
    def create_companies(self, count=10):
        """Create fake companies"""
        print(f"📊 Creating {count} companies...")
        
        # Valid HubSpot industry values (extracted from API error message)
        industries = [
            "ACCOUNTING", "AIRLINES_AVIATION", "ALTERNATIVE_DISPUTE_RESOLUTION",
            "ALTERNATIVE_MEDICINE", "ANIMATION", "APPAREL_FASHION", 
            "ARCHITECTURE_PLANNING", "ARTS_AND_CRAFTS", "AUTOMOTIVE",
            "AVIATION_AEROSPACE", "BANKING", "BIOTECHNOLOGY", "BROADCAST_MEDIA",
            "BUILDING_MATERIALS", "BUSINESS_SUPPLIES_AND_EQUIPMENT", "CAPITAL_MARKETS",
            "CHEMICALS", "CIVIC_SOCIAL_ORGANIZATION", "CIVIL_ENGINEERING",
            "COMMERCIAL_REAL_ESTATE", "COMPUTER_GAMES", "COMPUTER_HARDWARE",
            "COMPUTER_NETWORKING", "COMPUTER_SOFTWARE", "CONSTRUCTION",
            "CONSUMER_ELECTRONICS", "CONSUMER_GOODS", "CONSUMER_SERVICES",
            "COSMETICS", "DAIRY", "DEFENSE_SPACE", "DESIGN", "EDUCATION_MANAGEMENT",
            "E_LEARNING", "ELECTRICAL_ELECTRONIC_MANUFACTURING", "ENTERTAINMENT",
            "ENVIRONMENTAL_SERVICES", "EVENTS_SERVICES", "EXECUTIVE_OFFICE",
            "FACILITIES_SERVICES", "FARMING", "FINANCIAL_SERVICES", "FINE_ART",
            "FISHERY", "FITNESS", "FOOD_BEVERAGES", "FOOD_PRODUCTION",
            "FUND_RAISING", "FURNITURE", "GAMBLING_CASINOS", "GLASS_CERAMICS_CONCRETE",
            "GOVERNMENT_ADMINISTRATION", "GOVERNMENT_RELATIONS", "GRAPHIC_DESIGN",
            "HEALTH_WELLNESS_FITNESS", "HIGHER_EDUCATION", "HOSPITAL_HEALTH_CARE",
            "HOSPITALITY", "HUMAN_RESOURCES", "IMPORT_EXPORT", "INDIVIDUAL_FAMILY_SERVICES",
            "INDUSTRIAL_AUTOMATION", "INFORMATION_SERVICES", "INFORMATION_TECHNOLOGY_SERVICES",
            "INSURANCE", "INTERNATIONAL_AFFAIRS", "INTERNATIONAL_TRADE_DEVELOPMENT",
            "INTERNET", "INVESTMENT_BANKING", "INVESTMENT_MANAGEMENT", "JUDICIARY",
            "LAW_ENFORCEMENT", "LEGAL_SERVICES", "LEGISLATIVE_OFFICE", "LEISURE_TRAVEL_TOURISM",
            "LIBRARY", "LOGISTICS_SUPPLY_CHAIN", "LUXURY_GOODS_JEWELRY", "MACHINERY",
            "MANAGEMENT_CONSULTING", "MARITIME", "MARKET_RESEARCH", "MARKETING_ADVERTISING",
            "MECHANICAL_INDUSTRIAL_ENGINEERING", "MEDIA_PRODUCTION", "MEDICAL_DEVICES",
            "MEDICAL_PRACTICE", "MENTAL_HEALTH_CARE", "MILITARY", "MINING_METALS",
            "MOTION_PICTURES_FILM", "MUSEUMS_INSTITUTIONS", "MUSIC", "NANOTECHNOLOGY",
            "NEWSPAPERS", "NON_PROFIT_ORGANIZATION_MANAGEMENT", "OIL_ENERGY",
            "ONLINE_MEDIA", "OUTSOURCING_OFFSHORING", "PACKAGE_FREIGHT_DELIVERY",
            "PACKAGING_CONTAINERS", "PAPER_FOREST_PRODUCTS", "PERFORMING_ARTS",
            "PHARMACEUTICALS", "PHILANTHROPY", "PHOTOGRAPHY", "PLASTICS", "POLITICAL_ORGANIZATION",
            "PRIMARY_SECONDARY_EDUCATION", "PRINTING", "PROFESSIONAL_TRAINING_COACHING",
            "PROGRAM_DEVELOPMENT", "PUBLIC_POLICY", "PUBLIC_RELATIONS_COMMUNICATIONS",
            "PUBLIC_SAFETY", "PUBLISHING", "RAILROAD_MANUFACTURE", "RANCHING",
            "REAL_ESTATE", "RECREATIONAL_FACILITIES_SERVICES", "RELIGIOUS_INSTITUTIONS",
            "RENEWABLES_ENVIRONMENT", "RESEARCH", "RESTAURANTS", "RETAIL",
            "SECURITY_INVESTIGATIONS", "SEMICONDUCTORS", "SHIPBUILDING", "SPORTING_GOODS",
            "SPORTS", "STAFFING_RECRUITING", "SUPERMARKETS", "TELECOMMUNICATIONS",
            "TEXTILES", "THINK_TANKS", "TOBACCO", "TRANSLATION_LOCALIZATION",
            "TRANSPORTATION_TRUCKING_RAILROAD", "UTILITIES", "VENTURE_CAPITAL_PRIVATE_EQUITY",
            "VETERINARY", "WAREHOUSING", "WHOLESALE", "WINE_SPIRITS", "WIRELESS",
            "WRITING_EDITING"
        ]
        
        companies = []
        for i in range(count):
            company_name = fake.company()
            domain = fake.domain_name()
            
            data = {
                "properties": {
                    "name": company_name,
                    "domain": domain,
                    "industry": random.choice(industries),
                    "city": fake.city(),
                    "state": fake.state(),
                    "country": "United States",
                    "phone": fake.phone_number(),
                    "description": fake.catch_phrase(),
                    "numberofemployees": str(random.randint(10, 1000)),
                    "annualrevenue": str(random.randint(100000, 10000000))
                }
            }
            
            try:
                result = self._request('POST', '/crm/v3/objects/companies', data)
                companies.append(result)
                print(f"  ✅ {company_name} (ID: {result['id']})")
            except Exception as e:
                print(f"  ❌ {company_name}: {str(e)}")
        
        return companies
    
    def create_pipeline(self, name, stages):
        """Create deal pipeline with stages"""
        print(f"🔄 Creating pipeline: {name}")
        
        # Check if pipeline already exists
        try:
            existing_pipelines = self._request('GET', '/crm/v3/pipelines/deals')
            for pipeline in existing_pipelines.get('results', []):
                if pipeline.get('label') == name:
                    print(f"  ✅ Pipeline '{name}' already exists (ID: {pipeline['id']})")
                    return pipeline
        except Exception as e:
            print(f"  ⚠️  Could not check existing pipelines: {str(e)}")
        
        # Create new pipeline
        pipeline_stages = []
        for i, (stage_name, probability) in enumerate(stages):
            pipeline_stages.append({
                "label": stage_name,
                "displayOrder": i,
                "metadata": {
                    "probability": str(probability),
                    "closedWon": probability == 1.0
                }
            })
        
        data = {
            "label": name,
            "displayOrder": 0,
            "stages": pipeline_stages
        }
        
        try:
            result = self._request('POST', '/crm/v3/pipelines/deals', data)
            print(f"  ✅ Pipeline created (ID: {result['id']}) with {len(stages)} stages")
            return result
        except Exception as e:
            # Handle duplicate pipeline error
            if "already exists" in str(e):
                print(f"  ⚠️  Pipeline '{name}' already exists, finding existing one...")
                try:
                    existing_pipelines = self._request('GET', '/crm/v3/pipelines/deals')
                    for pipeline in existing_pipelines.get('results', []):
                        if pipeline.get('label') == name:
                            print(f"  ✅ Using existing pipeline (ID: {pipeline['id']})")
                            return pipeline
                    
                    # If we can't find the specific pipeline, use the first available one
                    if existing_pipelines.get('results'):
                        pipeline = existing_pipelines['results'][0]
                        print(f"  ✅ Using default pipeline: {pipeline['label']} (ID: {pipeline['id']})")
                        return pipeline
                except:
                    pass
                    
            # Re-raise the original error if we can't handle it
            raise e
    
    def create_deals(self, companies, pipeline, count=20):
        """Create fake deals and move through stages"""
        print(f"💰 Creating {count} deals...")
        
        stages = pipeline['stages']
        deals = []
        
        # Better deal name templates
        deal_templates = [
            "{} Implementation",
            "{} Renewal",
            "{} Upgrade",
            "{} Service Contract",
            "{} Partnership",
            "{} Integration Project",
            "{} Consulting",
            "{} License Agreement"
        ]
        
        for i in range(count):
            company = random.choice(companies)
            stage = random.choice(stages)
            
            # Generate better deal names
            service = random.choice([
                "Software", "Platform", "Analytics", "CRM", "Marketing", 
                "Security", "Cloud", "Mobile", "AI", "Enterprise"
            ])
            deal_name = random.choice(deal_templates).format(service)
            
            # Generate random close date
            close_date = fake.date_between(start_date='today', end_date='+6M')
            close_date_timestamp = close_date.strftime('%Y-%m-%d')
            close_date_dt = datetime.strptime(close_date_timestamp, '%Y-%m-%d')
            close_date_ms = int(close_date_dt.timestamp()) * 1000
            
            data = {
                "properties": {
                    "dealname": f"{deal_name} - {company['properties']['name']}",
                    "amount": str(random.randint(5000, 500000)),
                    "dealstage": stage['id'],
                    "pipeline": pipeline['id'],
                    "closedate": str(close_date_ms),
                    "dealtype": random.choice(["newbusiness", "existingbusiness", "renewal"]),
                    "description": fake.text(max_nb_chars=200)
                },
                "associations": [{
                    "to": {"id": company['id']},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 5}]
                }]
            }
            
            try:
                result = self._request('POST', '/crm/v3/objects/deals', data)
                deals.append(result)
                deal_name = result['properties']['dealname']
                stage_name = stage['label']
                amount = result['properties']['amount']
                print(f"  ✅ {deal_name} - ${amount} ({stage_name})")
            except Exception as e:
                print(f"  ❌ Deal creation failed: {str(e)}")
        
        return deals
    
    def move_deals_through_stages(self, deals, pipeline, sample_count=5):
        """Move some deals through all pipeline stages"""
        print(f"🔄 Moving {sample_count} deals through pipeline stages...")
        
        stages = pipeline['stages']
        sample_deals = random.sample(deals, min(sample_count, len(deals)))
        
        for deal in sample_deals:
            deal_id = deal['id']
            deal_name = deal['properties']['dealname']
            
            print(f"  📈 Moving: {deal_name}")
            
            for i, stage in enumerate(stages):
                try:
                    data = {
                        "properties": {
                            "dealstage": stage['id'],
                            "pipeline": pipeline['id']
                        }
                    }
                    
                    self._request('PATCH', f'/crm/v3/objects/deals/{deal_id}', data)
                    print(f"    → {stage['label']}")
                    
                    if i < len(stages) - 1:  # Don't wait after last stage
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"    ❌ Failed to move to {stage['label']}: {str(e)}")
                    break
    
    def seed_all_data(self, companies_count=15, deals_count=30, move_deals_count=8):
        """Seed all data: companies, pipeline, deals, and stage movements"""
        print("🚀 Starting HubSpot data seeding...")
        print("="*50)
        
        # 1. Create companies
        companies = self.create_companies(companies_count)
        successful_companies = [c for c in companies if 'id' in c]
        
        if not successful_companies:
            print("❌ No companies created successfully. Exiting.")
            return
        
        # 2. Try to create sales pipeline (skip if no permission)
        pipeline = None
        try:
            stages = [
                ("Prospecting", 0.1),
                ("Qualified Lead", 0.2),
                ("Meeting Scheduled", 0.4),
                ("Proposal Sent", 0.6),
                ("Negotiation", 0.8),
                ("Closed Won", 1.0),
                ("Closed Lost", 0.0)
            ]
            
            # Generate random pipeline name to avoid duplicates
            pipeline_names = [
                "Sales Pipeline", "Revenue Pipeline", "Business Pipeline", 
                "Growth Pipeline", "Customer Pipeline", "Deal Pipeline",
                "Opportunity Pipeline", "Lead Pipeline"
            ]
            random_name = f"{random.choice(pipeline_names)} {random.randint(1000, 9999)}"
            
            pipeline = self.create_pipeline(random_name, stages)
        except Exception as e:
            if "MISSING_SCOPES" in str(e):
                print("⚠️  Skipping pipeline creation - missing crm.schemas.deals.write scope")
                print("📝 Using default pipeline instead")
                # Get default pipeline
                try:
                    pipelines_response = self._request('GET', '/crm/v3/pipelines/deals')
                    if pipelines_response.get('results'):
                        pipeline = pipelines_response['results'][0]  # Use first available pipeline
                        print(f"✅ Using existing pipeline: {pipeline['label']}")
                except:
                    print("❌ Cannot access pipelines. Deals will use default settings.")
            else:
                print(f"❌ Pipeline creation failed: {str(e)}")
        
        # 3. Create deals
        if pipeline:
            deals = self.create_deals(successful_companies, pipeline, deals_count)
            successful_deals = [d for d in deals if 'id' in d]
            
            # 4. Move some deals through stages
            if successful_deals and len(pipeline.get('stages', [])) > 1:
                self.move_deals_through_stages(successful_deals, pipeline, move_deals_count)
        else:
            print("⚠️  Skipping deal creation - no pipeline available")
            successful_deals = []
        
        # 5. Summary
        print("\n" + "="*50)
        print("✅ Data seeding completed!")
        print(f"📊 Companies created: {len(successful_companies)}")
        if pipeline:
            print(f"🔄 Pipeline: {pipeline['label']} ({len(pipeline.get('stages', []))} stages)")
            print(f"💰 Deals created: {len(successful_deals)}")
            if successful_deals:
                print(f"📈 Deals moved through stages: {min(move_deals_count, len(successful_deals))}")
        
        return {
            'companies': successful_companies,
            'pipeline': pipeline,
            'deals': successful_deals if pipeline else []
        }

def main():
    """Main function"""
    print("🎯 HubSpot Data Seeder with Faker")
    print("="*40)
    
    # Get API token - remove hardcoded token for security
    api_token = "pat-na2-9a92dd2d-66bf-46f2-abe0-2b862368c823"
    if not api_token:
        api_token = input("Enter HubSpot API token: ").strip()
    
    if not api_token:
        print("❌ No API token provided")
        return
    
    try:
        seeder = HubSpotSeeder(api_token)
        
        # Quick seed or custom
        choice = input("\n1. Quick seed (15 companies, 30 deals)\n2. Custom counts\nChoice (1/2): ").strip()
        
        if choice == '2':
            companies = int(input("Companies to create: ") or 15)
            deals = int(input("Deals to create: ") or 30)
            move_deals = int(input("Deals to move through stages: ") or 8)
            seeder.seed_all_data(companies, deals, move_deals)
        else:
            seeder.seed_all_data()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()