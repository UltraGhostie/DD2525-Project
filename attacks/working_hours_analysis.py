import json
import os

import matplotlib.pyplot as plt
import numpy as np

def analyze_working_hours(json_path, sensitivity):
    with open(json_path, 'r') as f:
        history = json.load(f)

    movements = []
    scooter_states = {} # uuid -> (last_seen_time, last_lat, last_lon)
    
    for entry in history:
        time = entry['time']
        current_available = {u['uuid']: u for u in entry['available_units']}
        
        # Check for scooters that disappeared (rented)
        for uuid in list(scooter_states.keys()):
            if uuid not in current_available and (isinstance(scooter_states[uuid], tuple) and scooter_states[uuid][0] != 'rented'):
                state = scooter_states[uuid]
                # Scooter was picked up at state[0] time at (state[1], state[2]) coordinates
                scooter_states[uuid] = ('rented', state[0], state[1], state[2])

        # Check for scooters that appeared (returned)
        for uuid, unit in current_available.items():
            if uuid in scooter_states:
                state = scooter_states[uuid]
                if state[0] == 'rented':
                    _, pickup_time, pickup_lat, pickup_lon = state
                    movements.append({
                        'uuid': uuid,
                        'pickup_time': pickup_time,
                        'pickup_loc': (pickup_lat, pickup_lon),
                        'dropoff_time': time,
                        'dropoff_loc': (unit['lat'], unit['lon'])
                    })
            scooter_states[uuid] = (time, unit['lat'], unit['lon'])

    # Group movements by "person"
    # Based on the evening return location, find the closest morning pickup location, calculate the duration of work.
    # Morning: 360-660 (6:00-11:00) pretended to be 6:00-11:00
    # Evening: 900-1200 (15:00-20:00) pretended to be 15:00-20:00
    
    morning_pickups = [m for m in movements if 360 <= m['dropoff_time'] <= 700]
    evening_dropoffs = [m for m in movements if 900 <= m['pickup_time'] <= 1200]
    
    work_sessions = []
    
    def dist(loc1, loc2):
        return np.sqrt((loc1[0] - loc2[0])**2 + (loc1[1] - loc2[1])**2)
    
    # Loop through morning pickups and find matching evening dropoffs
    used_evening = set()
    for m_drop in morning_pickups:
        best_match = None
        min_dist = float('inf')
        
        for i, e_pick in enumerate(evening_dropoffs):
            if i in used_evening: continue
            
            # Distance between where they arrived in the morning and where they started in the evening
            d = dist(m_drop['dropoff_loc'], e_pick['pickup_loc'])
            if d < min_dist:
                min_dist = d
                best_match = i
                
        if best_match is not None and min_dist < sensitivity: # Set threshold depending on how close you expect.
            used_evening.add(best_match)
            e_pick = evening_dropoffs[best_match]
            work_sessions.append({
                'start': m_drop['dropoff_time'],
                'end': e_pick['pickup_time'],
                'dist': min_dist
            })
    # we use sensitivity here as maybe if some scooter is rented very far away from a drop off it could be another person
    return work_sessions

def plot_working_hours(sessions, sensitivity):
    if not sessions:
        print(f"No work sessions identified. Maybe too high sensitivity: {sensitivity}")
        return

    plt.figure(figsize=(12, 12))
    
    sessions.sort(key=lambda x: x['start'])
    
    for i, s in enumerate(sessions):
        start_hour = s['start'] / 60
        end_hour = s['end'] / 60
        duration = end_hour - start_hour
        
        plt.barh(i, duration, left=start_hour, color='skyblue', edgecolor='navy', alpha=0.8)
        plt.text(start_hour + 0.1, i, f" {duration:.1f}h", va='center', ha='left', fontweight='bold')

    plt.yticks(range(len(sessions)), [f"Person {i+1}" for i in range(len(sessions))])
    plt.xlabel("Time of Day (Hours)")
    plt.title(f"Assumed Working Hours based on Scooter Commutes (Sensitivity: {sensitivity})")
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Set x-axis ticks to show hours
    plt.xticks(range(6, 22))
    plt.xlim(6, 21)
    
    # Add vertical lines for typical 9-5 hours
    plt.axvline(x=9, color='red', linestyle=':', alpha=0.5, label='Typical Start (9:00)')
    plt.axvline(x=17, color='green', linestyle=':', alpha=0.5, label='Typical End (17:00)')
    plt.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig("working_hours_analysis.png")
    print(f"Graph saved as working_hours_analysis.png with {len(sessions)} identified persons.")

if __name__ == "__main__":
    # Sensitivity
    sensitivity = 0.05
    # Get the directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build the path to response.json (same folder)
    json_path = os.path.join(script_dir, "response.json")

    sessions = analyze_working_hours(json_path, sensitivity)
    plot_working_hours(sessions, sensitivity)
