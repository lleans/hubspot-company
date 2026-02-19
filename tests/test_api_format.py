#!/usr/bin/env python3

import requests
import json

def test_api_format():
    """Test the API with different request formats"""
    
    # Test with the legacy format (your credentials format)
    legacy_payload = {
        "connection_id": "123e4567-e89b-12d3-a456-426612264100",
        "token": "pat-na2-9a92dd2d-66bf-46f2-abe0-2b862368c823",
        "config": {
            "extract_companies": True,
            "extract_deals": True,
            "extract_pipelines": True,
            "batch_size": 100
        }
    }
    
    # Test with the new format
    new_payload = {
        "config": {
            "scanId": "123e4567-e89b-12d3-a456-426612264100",
            "auth": {
                "accessToken": "pat-na2-9a92dd2d-66bf-46f2-abe0-2b862368c823"
            },
            "type": ["companies", "deals", "pipelines"],
            "extraction": {
                "batch_size": 100
            }
        }
    }
    
    print("Testing legacy format:")
    print(json.dumps(legacy_payload, indent=2))
    print("\nTesting new format:")
    print(json.dumps(new_payload, indent=2))

if __name__ == "__main__":
    test_api_format()
