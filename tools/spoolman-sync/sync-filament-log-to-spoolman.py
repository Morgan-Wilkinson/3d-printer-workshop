#!/usr/bin/env python3
"""
Filament Log to Spoolman Sync Tool

This script synchronizes filament log data with Spoolman by:
1. Reading filament log export JSON data
2. Clearing existing Spoolman data (optional)
3. Creating matching vendors, filaments, and spools in Spoolman
4. Mapping filament log IDs to Spoolman IDs for future usage logging

Usage:
    python sync-filament-log-to-spoolman.py <filament_log_export.json> [--clear-spoolman]
"""

import json
import requests
import sys
from datetime import datetime

# Spoolman API endpoint
SPOOLMAN_API = "http://spoolman.local/api/v1"
REQUEST_TIMEOUT = 10

# Mapping file to store filament log ID -> Spoolman ID relationships
MAPPING_FILE = "spoolman_id_mapping.json"

def load_filament_log_data(json_file):
    """Load data from Filament Log export JSON"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

def load_mapping():
    """Load existing ID mapping"""
    try:
        with open(MAPPING_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Warning: Could not load mapping file: {e}")
        return {}

def save_mapping(mapping):
    """Save ID mapping to file"""
    try:
        with open(MAPPING_FILE, 'w') as f:
            json.dump(mapping, f, indent=2)
        print(f"✓ Saved ID mapping to {MAPPING_FILE}")
    except Exception as e:
        print(f"Warning: Could not save mapping file: {e}")

def clear_spoolman():
    """Delete all existing spools, filaments, and vendors"""
    print("Clearing existing Spoolman data...")
    
    # Delete all spools
    try:
        response = requests.get(f"{SPOOLMAN_API}/spool", timeout=REQUEST_TIMEOUT)
        spools = response.json() if response.status_code == 200 else []
        print(f"Found {len(spools)} spools to delete")
        for spool in spools:
            delete_response = requests.delete(f"{SPOOLMAN_API}/spool/{spool['id']}", timeout=REQUEST_TIMEOUT)
            if delete_response.status_code in [200, 204]:
                print(f"✓ Deleted spool {spool['id']}")
    except Exception as e:
        print(f"Error deleting spools: {e}")
    
    # Delete all filaments
    try:
        response = requests.get(f"{SPOOLMAN_API}/filament", timeout=REQUEST_TIMEOUT)
        filaments = response.json() if response.status_code == 200 else []
        print(f"Found {len(filaments)} filaments to delete")
        for filament in filaments:
            delete_response = requests.delete(f"{SPOOLMAN_API}/filament/{filament['id']}", timeout=REQUEST_TIMEOUT)
            if delete_response.status_code in [200, 204]:
                print(f"✓ Deleted filament {filament['id']}")
    except Exception as e:
        print(f"Error deleting filaments: {e}")
    
    # Delete all vendors
    try:
        response = requests.get(f"{SPOOLMAN_API}/vendor", timeout=REQUEST_TIMEOUT)
        vendors = response.json() if response.status_code == 200 else []
        print(f"Found {len(vendors)} vendors to delete")
        for vendor in vendors:
            delete_response = requests.delete(f"{SPOOLMAN_API}/vendor/{vendor['id']}", timeout=REQUEST_TIMEOUT)
            if delete_response.status_code in [200, 204]:
                print(f"✓ Deleted vendor {vendor['id']}")
    except Exception as e:
        print(f"Error deleting vendors: {e}")
    
    print("Spoolman cleared.")

def get_or_create_vendor(brand, existing_vendors):
    """Get existing vendor or create new one"""
    if not brand:
        return None
    
    # Search for existing vendor
    for vendor in existing_vendors:
        if vendor.get('name', '').lower() == brand.lower():
            return vendor
    
    # Create new vendor
    vendor_payload = {
        "name": brand,
        "registered": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(f"{SPOOLMAN_API}/vendor", json=vendor_payload, timeout=REQUEST_TIMEOUT)
        if response.status_code in [200, 201]:
            print(f"✓ Created vendor: {brand}")
            return response.json()
        else:
            print(f"✗ Failed to create vendor: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"✗ Error creating vendor: {e}")
        return None

def get_or_create_filament(filament_data, existing_filaments, existing_vendors):
    """Get existing filament or create new one"""
    material = filament_data.get('material', '').upper()
    color_name = filament_data.get('colorName', '')
    brand = filament_data.get('brand', '')
    line = filament_data.get('line', material)
    
    # Include color in the name since Spoolman doesn't have a separate color field
    filament_name = f"{line} - {color_name}" if color_name else line
    
    # Search for existing filament
    for filament in existing_filaments:
        if filament.get('name', '') == filament_name:
            return filament
    
    # Get or create vendor first
    vendor = get_or_create_vendor(brand, existing_vendors) if brand else None
    vendor_id = vendor['id'] if vendor else None
    
    # Create new filament
    filament_payload = {
        "name": filament_name,
        "color": {
            "name": color_name,
            "hex": filament_data.get('colorHex', '#000000')
        },
        "material": material,
        "vendor_id": vendor_id,
        "price": filament_data.get('pricePaid', 0),
        "weight": filament_data.get('netWeightG', 1000),
        "spool_weight": 0,
        "density": 1.24,  # Standard PLA density
        "diameter": 1.75,  # Standard filament diameter
        "registered": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(f"{SPOOLMAN_API}/filament", json=filament_payload, timeout=REQUEST_TIMEOUT)
        if response.status_code in [200, 201]:
            print(f"✓ Created filament: {brand} - {filament_name}")
            return response.json()
        else:
            print(f"✗ Failed to create filament: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"✗ Error creating filament: {e}")
        return None

def create_spool(spool_data, filament_id):
    """Create a spool in Spoolman"""
    initial_weight = spool_data.get('netWeightG', 1000)
    remaining_weight = spool_data.get('remainingG', initial_weight)
    
    spool_payload = {
        "filament_id": filament_id,
        "price": spool_data.get('pricePaid', 0),
        "first_used": spool_data.get('purchaseDate', None),
        "last_used": None,
        "registered": datetime.now().isoformat(),
        "note": spool_data.get('notes', ''),
        "lot_nr": '',
        "archive": spool_data.get('archived', False),
        "remaining_weight": remaining_weight
    }
    
    try:
        response = requests.post(f"{SPOOLMAN_API}/spool", json=spool_payload, timeout=REQUEST_TIMEOUT)
        if response.status_code in [200, 201]:
            print(f"✓ Created spool: {spool_data.get('brand')} - {spool_data.get('colorName')}")
            return response.json()
        else:
            print(f"✗ Failed to create spool: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"✗ Error creating spool: {e}")
        return None

def sync_data(json_file, clear_first=False):
    """Main sync function"""
    print("Starting Filament Log to Spoolman sync...")
    print(f"Loading data from: {json_file}")
    
    # Load Filament Log data
    data = load_filament_log_data(json_file)
    if not data:
        print("Failed to load data. Exiting.")
        return
    
    spools = data.get('spools', [])
    print(f"Found {len(spools)} spools in filament log")
    
    # Clear Spoolman if requested
    if clear_first:
        clear_spoolman()
    
    # Get existing filaments from Spoolman
    try:
        response = requests.get(f"{SPOOLMAN_API}/filament", timeout=REQUEST_TIMEOUT)
        existing_filaments = response.json() if response.status_code == 200 else []
        print(f"Found {len(existing_filaments)} existing filaments in Spoolman")
    except Exception as e:
        print(f"Error fetching existing filaments: {e}")
        existing_filaments = []
    
    # Get existing vendors from Spoolman
    try:
        response = requests.get(f"{SPOOLMAN_API}/vendor", timeout=REQUEST_TIMEOUT)
        existing_vendors = response.json() if response.status_code == 200 else []
        print(f"Found {len(existing_vendors)} existing vendors in Spoolman")
    except Exception as e:
        print(f"Error fetching existing vendors: {e}")
        existing_vendors = []
    
    # Load existing mapping
    id_mapping = load_mapping()
    
    # Process spools
    spool_count = 0
    for spool in spools:
        if spool.get('archived', False):
            print(f"Skipping archived spool: {spool.get('brand')} - {spool.get('colorName')}")
            continue
        
        filament_log_id = spool.get('id')
        color_name = spool.get('colorName', '')
        line = spool.get('line', spool.get('material', ''))
        filament_name = f"{line} - {color_name}" if color_name else line
        
        print(f"Processing spool: {spool.get('brand')} - {filament_name}")
        
        # Get or create filament
        filament = get_or_create_filament(spool, existing_filaments, existing_vendors)
        if filament:
            # Create spool
            spool_result = create_spool(spool, filament['id'])
            if spool_result:
                spool_count += 1
                # Map filament log ID to Spoolman ID
                id_mapping[filament_log_id] = spool_result['id']
                print(f"  Mapped filament log ID {filament_log_id} -> Spoolman ID {spool_result['id']}")
    
    # Save mapping
    save_mapping(id_mapping)
    
    print(f"\nSync complete!")
    print(f"Created {spool_count} spools in Spoolman")
    print(f"ID mapping saved to {MAPPING_FILE}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync-filament-log-to-spoolman.py <filament_log_export.json> [--clear-spoolman]")
        print("\nTo export your Filament Log data:")
        print("1. Open http://3dworkshop.local/pages/filament-log.html")
        print("2. Click 'Export backup'")
        print("3. Save the JSON file")
        print("4. Run this script with the file path")
        print("\nUse --clear-spoolman to delete all existing Spoolman data before sync")
        sys.exit(1)
    
    json_file = sys.argv[1]
    clear_first = '--clear-spoolman' in sys.argv
    
    sync_data(json_file, clear_first)