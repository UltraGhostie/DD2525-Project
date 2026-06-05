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
    # Morning: 360-660 (6:00-11:00)
    # Evening: 900-1200 (15:00-20:00)
    
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
                
        if best_match is not None and min_dist < sensitivity:
            used_evening.add(best_match)
            e_pick = evening_dropoffs[best_match]
            # The "work location" is m_drop['dropoff_loc'] (and e_pick['pickup_loc'] which is very close)
            work_sessions.append({
                'start': m_drop['dropoff_time'],
                'end': e_pick['pickup_time'],
                'dist': min_dist,
                'location': m_drop['dropoff_loc']
            })
    return work_sessions

def plot_working_hours(sessions, sensitivity):
    if not sessions:
        print(f"No work sessions identified. Maybe too high sensitivity: {sensitivity}")
        return

    plt.figure(figsize=(12, 12))
    
    sessions.sort(key=lambda x: x['start'])
    
    def dist(loc1, loc2):
        return np.sqrt((loc1[0] - loc2[0])**2 + (loc1[1] - loc2[1])**2)

    # Group by location
    location_groups = [] # list of (representative_loc, color_index)
    session_colors = []
    
    # Define a set of colors
    colors = plt.get_cmap('tab10', 10)
    
    for s in sessions:
        loc = s['location']
        found_group = False
        for i, (group_loc, group_idx) in enumerate(location_groups):
            if dist(loc, group_loc) < sensitivity:
                session_colors.append(colors(group_idx))
                found_group = True
                break
        
        if not found_group:
            new_idx = len(location_groups) % 10
            location_groups.append((loc, new_idx))
            session_colors.append(colors(new_idx))

    for i, s in enumerate(sessions):
        start_hour = s['start'] / 60
        end_hour = s['end'] / 60
        duration = end_hour - start_hour
        
        plt.barh(i, duration, left=start_hour, color=session_colors[i], edgecolor='black', alpha=0.8)
        plt.text(start_hour + 0.1, i, f" {duration:.1f}h", va='center', ha='left', fontweight='bold')

    plt.yticks(range(len(sessions)), [f"Person {i+1}" for i in range(len(sessions))])
    plt.xlabel("Time of Day (Hours)")
    plt.title(f"Assumed Working Hours colored by Location (Sensitivity: {sensitivity})")
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    plt.xticks(range(6, 22))
    plt.xlim(6, 21)
    
    plt.axvline(x=9, color='red', linestyle=':', alpha=0.5, label='Typical Start (9:00)')
    plt.axvline(x=17, color='green', linestyle=':', alpha=0.5, label='Typical End (17:00)')
    plt.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig("working_hours_location_analysis.png")
    print(f"Graph saved as working_hours_location_analysis.png with {len(sessions)} identified persons.")

if __name__ == "__main__":
    sensitivity = 0.01
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "response.json")

    sessions = analyze_working_hours(json_path, sensitivity)
    plot_working_hours(sessions, sensitivity)
