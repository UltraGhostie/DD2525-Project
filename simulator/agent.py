import requests
import random
import time
import math

BASE_URL = "http://localhost:8000/api"
SCOOTER_SPEED = 0.02 # units per minute
WALKING_SPEED = 0.005 # units per minute

class Person:
    def __init__(self, id, home, destination, start_time, end_time):
        self.id = id
        self.home = home
        self.destination = destination
        self.start_time = start_time
        self.end_time = end_time
        self.current_scooter = None

    def find_and_rent_scooter(self, current_pos):
        response = requests.get(f"{BASE_URL}/stockholm")
        if response.status_code != 200:
            print(f"Person {self.id} failed to get available scooters")
            return False, 0
        
        data = response.json()
        scooters = data.get("available_units", [])
        if not scooters:
            print(f"Person {self.id} found no available scooters")
            return False, 0
        
        # Find closest scooter
        closest_scooter = min(scooters, key=lambda s: math.sqrt((s['lat'] - current_pos[0])**2 + (s['lon'] - current_pos[1])**2))
        
        # Calculate distance to scooter (person walking to scooter)
        walk_dist = math.sqrt((closest_scooter['lat'] - current_pos[0])**2 + (closest_scooter['lon'] - current_pos[1])**2)
        
        rent_response = requests.post(f"{BASE_URL}/rent", json={"uuid": closest_scooter["uuid"]})
        if rent_response.status_code == 200:
            self.current_scooter = rent_response.json()["scooter"]
            print(f"Person {self.id} rented scooter {self.current_scooter['uuid']} after walking {walk_dist:.4f} units")
            return True, walk_dist
        else:
            print(f"Person {self.id} failed to rent scooter {closest_scooter['uuid']}")
            return False, 0

    def return_scooter(self, destination_pos):
        if not self.current_scooter:
            return False
        
        return_response = requests.post(f"{BASE_URL}/return", json={
            "uuid": self.current_scooter["uuid"],
            "lat": destination_pos[0],
            "lon": destination_pos[1]
        })
        if return_response.status_code == 200:
            print(f"Person {self.id} returned scooter {self.current_scooter['uuid']} at {destination_pos}")
            self.current_scooter = None
            return True
        else:
            print(f"Person {self.id} failed to return scooter {self.current_scooter['uuid']}")
            return False

def generate_coordinates():
    return random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25)

def main():
    school = generate_coordinates()
    workplaces = [generate_coordinates() for _ in range(random.randint(1, 4))]
    destinations = [school] + workplaces
    
    people = []
    for i in range(12):
        home = generate_coordinates()
        dest = random.choice(destinations)
        # Random morning start time between 6 and 9 (60 min increments for simplicity or random)
        start_time = random.randint(360, 540) 
        # Random evening end time between 15 and 18
        end_time = random.randint(900, 1080)
        people.append(Person(i, home, dest, start_time, end_time))

    # Sort people by their start time to simulate sequentially
    people.sort(key=lambda p: p.start_time)

    current_sim_time = 0

    print("--- Starting Morning Commute ---")
    for person in people:
        # Advance time to person's start time
        if person.start_time > current_sim_time:
            advance = person.start_time - current_sim_time
            requests.post(f"{BASE_URL}/advance_time", json={"amount": advance})
            current_sim_time = person.start_time
            print(f"Time advanced to {current_sim_time}")

        success, walk_dist = person.find_and_rent_scooter(person.home)
        if success:
            # Calculate walking time to scooter
            walk_time = int(walk_dist / WALKING_SPEED)
            if walk_time > 0:
                requests.post(f"{BASE_URL}/advance_time", json={"amount": walk_time})
                current_sim_time += walk_time
                print(f"Person {person.id} walked to scooter for {walk_time} min")

            # Calculate distance and travel time with scooter
            scooter_start_pos = (person.current_scooter['lat'], person.current_scooter['lon'])
            trip_dist = math.sqrt((person.destination[0] - scooter_start_pos[0])**2 + (person.destination[1] - scooter_start_pos[1])**2)
            travel_time = max(1, int(trip_dist / SCOOTER_SPEED))
            
            requests.post(f"{BASE_URL}/advance_time", json={"amount": travel_time})
            current_sim_time += travel_time
            person.return_scooter(person.destination)
            print(f"Person {person.id} traveled {trip_dist:.4f} units in {travel_time} min")

    # Sort people by their end time for the return trip
    people.sort(key=lambda p: p.end_time)

    print("\n--- Starting Evening Commute ---")
    for person in people:
        # Advance time to person's end time
        if person.end_time > current_sim_time:
            advance = person.end_time - current_sim_time
            requests.post(f"{BASE_URL}/advance_time", json={"amount": advance})
            current_sim_time = person.end_time
            print(f"Time advanced to {current_sim_time}")

        success, walk_dist = person.find_and_rent_scooter(person.destination)
        if success:
            # Calculate walking time to scooter
            walk_time = int(walk_dist / WALKING_SPEED)
            if walk_time > 0:
                requests.post(f"{BASE_URL}/advance_time", json={"amount": walk_time})
                current_sim_time += walk_time
                print(f"Person {person.id} walked to scooter for {walk_time} min")

            # Calculate distance and travel time with scooter
            scooter_start_pos = (person.current_scooter['lat'], person.current_scooter['lon'])
            trip_dist = math.sqrt((person.home[0] - scooter_start_pos[0])**2 + (person.home[1] - scooter_start_pos[1])**2)
            travel_time = max(1, int(trip_dist / SCOOTER_SPEED))
            
            requests.post(f"{BASE_URL}/advance_time", json={"amount": travel_time})
            current_sim_time += travel_time
            person.return_scooter(person.home)
            print(f"Person {person.id} traveled {trip_dist:.4f} units in {travel_time} min")

if __name__ == "__main__":
    main()
