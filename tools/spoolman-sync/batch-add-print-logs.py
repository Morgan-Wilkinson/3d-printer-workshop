#!/usr/bin/env python3
"""
Add batch print logs to Filament Log and Spoolman
"""

import json
import requests
from datetime import datetime

# Load filament log data
with open('/Users/morganwilkinson/Downloads/filament-log-backup-2026-09-22.json', 'r') as f:
    data = json.load(f)

# Load ID mapping
with open('/Users/morganwilkinson/Development/A 3D Printer Workshop/tools/spoolman-sync/spoolman_id_mapping.json', 'r') as f:
    mapping = json.load(f)

# Map filament names to spool IDs
filament_to_spool = {
    "Bambu PLA Black": "CN1ihqTwxEKOZpW9SIDk",
    "Bambu PLA Grey": "lI1g6CT24z4QK1UFZgfr",
    "Bambu PLA Green": "UTmkyYYUeVm7uOCsNFYn",
    "Bambu PLA White": "bpK7xYG7aZXOWnUl6mxA",
}

# Print log data provided by user
print_logs = [
    {
        "model": "The best batman cat helmet ever!",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/18 15:49 - 2026/09/18 19:02",
        "filaments": [("Bambu PLA Black", 76.76)],
    },
    {
        "model": "Compact Poop Bin For X2D, P1S, P2S, X1C",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/18 19:39 - 2026/09/18 22:28",
        "filaments": [("Bambu PLA Grey", 149.02)],
    },
    {
        "model": "Filament Clip",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/18 23:11 - 2026/09/18 23:44",
        "filaments": [("Bambu PLA Green", 9.88)],
    },
    {
        "model": "Pixel 4 Leaf Clover Fidget",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/19 00:14 - 2026/09/19 04:53",
        "filaments": [("Bambu PLA Green", 59.98)],
    },
    {
        "model": "Everything Holder",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/19 10:54 - 2026/09/19 11:52",
        "filaments": [("Bambu PLA White", 25.74)],
    },
    {
        "model": "Japanese Samurai Incense Holder",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/19 12:22 - 2026/09/19 18:56",
        "filaments": [("Bambu PLA Black", 149.61)],
    },
    {
        "model": "Remote Control Caddy / Remote Control Holder",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/19 19:36 - 2026/09/19 22:19",
        "filaments": [("Bambu PLA Grey", 73.99)],
    },
    {
        "model": "Whale Fin Spoon Rest - Nautical",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/19 22:32 - 2026/09/20 01:44",
        "filaments": [("Bambu PLA Grey", 96.38)],
    },
    {
        "model": "Modern Desk Organizer",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/20 04:27 - 2026/09/20 09:10",
        "filaments": [("Bambu PLA Grey", 186.84)],
    },
    {
        "model": "Bambu Accessories Storage Toolbox P2S X2I H2S H2D (Box Bottom)",
        "plate_name": "Plate 1 - Box Bottom",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/20 14:43 - 2026/09/20 16:10",
        "filaments": [("Bambu PLA Grey", 71.25)],
    },
    {
        "model": "Bambu Accessories Storage Toolbox P2S X2I H2S H2D (Box Lid)",
        "plate_name": "Plate 2 - box lid",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/20 16:17 - 2026/09/20 17:28",
        "filaments": [("Bambu PLA Grey", 43.37), ("Bambu PLA White", 1.38)],
    },
    {
        "model": "Sheridan mom and Dad",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/21 18:45 - 2026/09/21 19:36",
        "filaments": [("Bambu PLA White", 7.89)],
    },
    {
        "model": "Sheridan mom and Dad (2nd print)",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/21 20:14 - 2026/09/21 22:46",
        "filaments": [("Bambu PLA White", 41.92)],
    },
    {
        "model": "Custom Dog Pet Name Medal Tag",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/21 23:06 - 2026/09/21 23:26",
        "filaments": [
            ("Bambu PLA Green", 3.04),
            ("Bambu PLA Black", 0.78),
            ("Bambu PLA White", 5.51),
        ],
    },
    {
        "model": "The Scallop Shell Vase - Organic Coastal Decor",
        "plate_name": "Plate 1",
        "build_plate": "Textured PEI Plate",
        "time": "2026/09/21 23:29",
        "filaments": [("Bambu PLA White", 85.54)],
    },
]

# Initialize usage tracking
usage_by_spool = {spool_id: 0 for spool_id in filament_to_spool.values()}

# Keep existing usage
if 'usage' not in data:
    data['usage'] = []

# Build set of existing usages to avoid duplicates
existing_keys = set()
for u in data['usage']:
    key = (u.get('spoolId'), u.get('date'), u.get('project'), u.get('amount'))
    existing_keys.add(key)

# Track which prints were added
added_prints = []

for idx, log in enumerate(print_logs, 1):
    # Parse end time from time string for date
    time_str = log['time']
    if ' - ' in time_str:
        end_time = time_str.split(' - ')[1]
    else:
        end_time = time_str
    date = end_time.split(' ')[0].replace('/', '-')
    
    # Create notes with plate info
    notes = f"{log['plate_name']}, {log['build_plate']}"
    
    # Add a usage entry for each filament used
    for filament, amount in log['filaments']:
        spool_id = filament_to_spool[filament]
        
        usage = {
            "id": f"usage{idx}_{spool_id}",
            "spoolId": spool_id,
            "date": date,
            "project": log['model'],
            "notes": notes,
            "amount": amount,
            "loggedAt": datetime.now().isoformat()
        }
        
        # Skip if exact duplicate already exists
        key = (spool_id, date, log['model'], amount)
        if key in existing_keys:
            print(f"Skipping duplicate: {log['model']} on {date} ({amount}g {filament})")
            continue
        existing_keys.add(key)
        
        usage_by_spool[spool_id] += amount
        data['usage'].append(usage)
        added_prints.append({
            'model': log['model'],
            'filament': filament,
            'amount': amount,
            'date': date
        })

# Update remaining amounts for spools
for spool in data['spools']:
    spool_id = spool['id']
    if spool_id in usage_by_spool:
        used = usage_by_spool[spool_id]
        current_remaining = spool.get('remainingG', spool.get('netWeightG', 0))
        spool['remainingG'] = round(current_remaining - used, 2)
        print(f"Updated {spool['colorName']} {spool['material']} spool: -{used}g, remaining {spool['remainingG']}g")

# Save updated filament log
with open('/Users/morganwilkinson/Downloads/filament-log-backup-2026-09-22.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"\nAdded {len(added_prints)} usage entries to filament log")

# Update Spoolman via API
SPOOLMAN_API = "http://spoolman.local/api/v1"
TIMEOUT = 10

print("\nUpdating Spoolman...")
for spool_id, used in usage_by_spool.items():
    spoolman_id = mapping.get(spool_id)
    if not spoolman_id:
        print(f"No mapping for spool {spool_id}")
        continue
    
    # Get current spool data
    try:
        resp = requests.get(f"{SPOOLMAN_API}/spool/{spoolman_id}", timeout=TIMEOUT)
        if resp.status_code == 200:
            current = resp.json()
            new_used = current.get('used_weight', 0) + used
            update_resp = requests.patch(
                f"{SPOOLMAN_API}/spool/{spoolman_id}",
                json={'used_weight': new_used},
                timeout=TIMEOUT
            )
            if update_resp.status_code in [200, 201]:
                print(f"Updated Spoolman spool {spoolman_id}: +{used}g (total used: {new_used}g)")
            else:
                print(f"Failed to update Spoolman spool {spoolman_id}: {update_resp.status_code}")
        else:
            print(f"Could not get Spoolman spool {spoolman_id}")
    except Exception as e:
        print(f"Error updating Spoolman spool {spoolman_id}: {e}")

print("\nDone!")
