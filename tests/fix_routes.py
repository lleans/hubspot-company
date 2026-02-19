#!/usr/bin/env python3

def fix_routes_file():
    """Add compatibility for legacy format in routes.py"""
    
    with open("../api/routes.py", "r") as f:
        content = f.read()
    
    # Find the section to replace
    old_section = """            # Parse request data
            data = request.get_json() or {}
            config = data.get("config", {})

            # Extract required fields from new format
            scan_id = config.get("scanId")
            auth_config = config.get("auth", {})
            token = auth_config.get("accessToken", "")"""
    
    new_section = """            # Parse request data
            data = request.get_json() or {}
            
            # Support both new nested format and legacy top-level format
            if "config" in data and data["config"].get("scanId"):
                # New format: nested config structure
                config = data.get("config", {})
                scan_id = config.get("scanId")
                auth_config = config.get("auth", {})
                token = auth_config.get("accessToken", "")
            else:
                # Legacy format: top-level fields
                scan_id = data.get("connection_id")
                token = data.get("token", "")
                config = data.get("config", {})
                
                # Map legacy extract_* flags to type array
                extraction_types = []
                if config.get("extract_companies", False):
                    extraction_types.append("companies")
                if config.get("extract_deals", False):
                    extraction_types.append("deals")
                if config.get("extract_pipelines", False):
                    extraction_types.append("pipelines")
                
                if extraction_types:
                    config["type"] = extraction_types"""
    
    if old_section in content:
        content = content.replace(old_section, new_section)
        
        with open("../api/routes.py", "w") as f:
            f.write(content)
        
        print("Successfully updated routes.py with legacy format compatibility")
    else:
        print("Could not find the target section in routes.py")

if __name__ == "__main__":
    fix_routes_file()
