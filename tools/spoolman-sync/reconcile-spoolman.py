#!/usr/bin/env python3
"""
Reconcile Filament Log usage with Spoolman by setting exact used_weight values
"""

import json
import requests

# Load filament log data
with open('/Users/morganwilkinson/Downloads/filament-log-backup-2026-09-22.json', 'r') as f:
    data = json.load(f)

# Load ID mapping
with open('/Users/morganwilkinson/Development/A 3D Printer Workshop/tools/spoolman-sync/spoolman_id_mapping.json', 'r') as f:
    mapping = json.load(f)

# Calculate total usage per spool from filament log
totals = {}
for usage in data.get('usage', []):
    spool_id = usage.get('spoolId')
    if spool_id:
        totals[spool_id] = totals.get(spool_id, 0) + usage.get('amount', 0)

print("Calculated totals from filament log:")
for spool_id, total in totals.items():
    spoolman_id = mapping.get(spool_id)
    print(f"  {spool_id} -> Spoolman {spoolman_id}: {total}g")

# Update Spoolman with exact used_weight
SPOOLMAN_API = "http://spoolman.local/api/v1"
TIMEOUT = 10

print("\nUpdating Spoolman...")
for spool_id, total in totals.items():
    spoolman_id = mapping.get(spool_id)
    if not spoolman_id:
        print(f"No mapping for {spool_id}")
        continue
    
    try:
        update_resp = requests.patch(
            f"{SPOOLMAN_API}/spool/{spoolman_id}",
            json={'used_weight': round(total, 2)},
            timeout=TIMEOUT
        )
        if update_resp.status_code in [200, 201]:
            result = update_resp.json()
            print(f"✓ Spool {spoolman_id} ({spool_id}): used_weight set to {total}g, remaining {result['remaining_weight']}g")
        else:
            print(f"✗ Failed to update spool {spoolman_id}: {update_resp.status_code} - {update_resp.text}")
    except Exception as e:
        print(f"✗ Error updating spool {spoolman_id}: {e}")

print("\nReconciliation complete!")
