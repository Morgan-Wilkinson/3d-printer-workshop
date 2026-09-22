#!/usr/bin/env python3
"""
Print Log Addition Tool

This script adds print logs to both Filament Log and Spoolman by:
1. Reading print log information from user input or extracted data
2. Checking for duplicates in both systems
3. Adding usage records to both Filament Log and Spoolman
4. Using ID mapping to match filament log spools to Spoolman spools

Usage:
    python add-print-log.py --spool-id <filament_log_id> --amount <grams> --date <YYYY-MM-DD> --project "<project_name>"
"""

import json
import requests
import sys
from datetime import datetime
from pathlib import Path

# Spoolman API endpoint
SPOOLMAN_API = "http://spoolman.local/api/v1"
REQUEST_TIMEOUT = 10

# Filament log file path (will be updated by user)
FILAMENT_LOG_FILE = None

# Mapping file
MAPPING_FILE = "spoolman_id_mapping.json"

def load_mapping():
    """Load ID mapping"""
    try:
        with open(MAPPING_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Mapping file {MAPPING_FILE} not found. Run sync-filament-log-to-spoolman.py first.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading mapping file: {e}")
        sys.exit(1)

def load_filament_log(json_file):
    """Load filament log data"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading filament log file: {e}")
        sys.exit(1)

def save_filament_log(data, json_file):
    """Save filament log data"""
    try:
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Updated filament log file: {json_file}")
    except Exception as e:
        print(f"Error saving filament log file: {e}")
        sys.exit(1)

def check_duplicate_usage(filament_log_data, spool_id, date, amount, project):
    """Check for similar usage records in filament log"""
    similar_entries = []
    
    for usage in filament_log_data.get('usage', []):
        # Check for same spool, date, and similar amount/project
        if usage.get('spoolId') == spool_id:
            if usage.get('date') == date:
                similar_entries.append(('Exact date match', usage))
            elif abs(float(usage.get('amount', 0)) - amount) < 5:  # Within 5g
                similar_entries.append(('Similar amount', usage))
            elif usage.get('project', '').lower() == project.lower():
                similar_entries.append(('Similar project name', usage))
    
    return similar_entries

def ask_about_duplicates(similar_entries):
    """Ask user about potential duplicates"""
    if not similar_entries:
        return True  # No duplicates, proceed
    
    print("\n⚠️  Potential duplicate entries found:")
    for i, (reason, entry) in enumerate(similar_entries, 1):
        print(f"{i}. {reason}:")
        print(f"   Date: {entry.get('date')}")
        print(f"   Amount: {entry.get('amount')}g")
        print(f"   Project: {entry.get('project')}")
        print(f"   Notes: {entry.get('notes', 'None')}")
    
    response = input("\nIs this a new print or a duplicate? (new/duplicate): ").strip().lower()
    return response == 'new'

def add_usage_to_filament_log(filament_log_data, spool_id, amount, date, project, notes=""):
    """Add usage record to filament log"""
    new_usage = {
        "id": f"id{datetime.now().timestamp()}".replace('.', ''),
        "spoolId": spool_id,
        "date": date,
        "amount": amount,
        "project": project,
        "notes": notes,
        "loggedAt": datetime.now().isoformat()
    }
    
    filament_log_data.setdefault('usage', []).insert(0, new_usage)
    print(f"✓ Added usage to filament log: {project} - {amount}g")

def add_usage_to_spoolman(spoolman_id, amount):
    """Add usage to Spoolman spool"""
    try:
        # Get current spool data
        response = requests.get(f"{SPOOLMAN_API}/spool/{spoolman_id}", timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            print(f"✗ Failed to get spool data: {response.status_code}")
            return False
        
        spool_data = response.json()
        current_used = spool_data.get('used_weight', 0)
        new_used = current_used + amount
        
        # Update spool with new used weight
        update_payload = {
            "used_weight": new_used
        }
        
        update_response = requests.patch(
            f"{SPOOLMAN_API}/spool/{spoolman_id}",
            json=update_payload,
            timeout=REQUEST_TIMEOUT
        )
        
        if update_response.status_code in [200, 201]:
            print(f"✓ Updated Spoolman spool {spoolman_id}: +{amount}g (total used: {new_used}g)")
            return True
        else:
            print(f"✗ Failed to update spool: {update_response.status_code} - {update_response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error updating Spoolman: {e}")
        return False

def add_print_log(spool_id, amount, date, project, notes="", filament_log_file=None):
    """Main function to add print log to both systems"""
    print("Adding print log to both Filament Log and Spoolman...")
    
    # Load mapping
    id_mapping = load_mapping()
    
    # Get Spoolman ID from mapping
    if spool_id not in id_mapping:
        print(f"Error: Spool ID {spool_id} not found in mapping. Run sync first.")
        sys.exit(1)
    
    spoolman_id = id_mapping[spool_id]
    print(f"Filament Log ID {spool_id} -> Spoolman ID {spoolman_id}")
    
    # Load filament log if file provided
    if filament_log_file:
        filament_log_data = load_filament_log(filament_log_file)
        
        # Check for duplicates
        similar_entries = check_duplicate_usage(filament_log_data, spool_id, date, amount, project)
        if not ask_about_duplicates(similar_entries):
            print("Skipping addition based on user input.")
            return
        
        # Add to filament log
        add_usage_to_filament_log(filament_log_data, spool_id, amount, date, project, notes)
        save_filament_log(filament_log_data, filament_log_file)
    
    # Add to Spoolman
    add_usage_to_spoolman(spoolman_id, amount)
    
    print("\n✓ Print log added successfully!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add-print-log.py --spool-id <filament_log_id> --amount <grams> --date <YYYY-MM-DD> --project \"<project_name>\" [--notes \"<notes>\"] [--filament-log <path_to_json>]")
        print("\nExample:")
        print("python add-print-log.py --spool-id CN1ihqTwxEKOZpW9SIDk --amount 76.76 --date 2026-09-18 --project \"Batman Cat Helmet\" --filament-log filament-log-backup.json")
        sys.exit(1)
    
    # Parse arguments
    args = sys.argv[1:]
    spool_id = None
    amount = None
    date = None
    project = None
    notes = ""
    filament_log_file = None
    
    for i in range(len(args)):
        if args[i] == '--spool-id' and i + 1 < len(args):
            spool_id = args[i + 1]
        elif args[i] == '--amount' and i + 1 < len(args):
            amount = float(args[i + 1])
        elif args[i] == '--date' and i + 1 < len(args):
            date = args[i + 1]
        elif args[i] == '--project' and i + 1 < len(args):
            project = args[i + 1]
        elif args[i] == '--notes' and i + 1 < len(args):
            notes = args[i + 1]
        elif args[i] == '--filament-log' and i + 1 < len(args):
            filament_log_file = args[i + 1]
    
    # Validate required arguments
    if not all([spool_id, amount, date, project]):
        print("Error: Missing required arguments. Need --spool-id, --amount, --date, and --project")
        sys.exit(1)
    
    add_print_log(spool_id, amount, date, project, notes, filament_log_file)