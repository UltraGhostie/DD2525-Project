from http.server import BaseHTTPRequestHandler, HTTPServer
from uuid import uuid4
import random
import json
from urllib.parse import urlparse
from math import sqrt
import copy

# Distance function from aggregate.py
def dist(x1, y1, x2, y2):
    return sqrt((abs(x1-x2)**2)+(abs(y1-y2)**2))

# DataBase for aggregate
class DataBase:
    def __init__(self):
        self._db = []          # Equivalent to available_units
        self._in_use = []      # Items currently rented
        self._groups = []      # Aggregated groups
        self._max_group_dist = 0.05
        self._group_map = {}   # uuid -> gid
        self._group_ref_count = {} # gid -> count
        self.history = []

    def add_items(self, items: list):
        for item in items:
            self.add_item(item)

    def add_item(self, item):
        self._db.append(item)
        uuid = item["uuid"]
        ilon = item["lon"]
        ilat = item["lat"]
        new_group = True
        for group in self._groups:
            gid = group["uuid"]
            glon = group["lon"]
            glat = group["lat"]
            if dist(ilon, ilat, glon, glat) <= self._max_group_dist:
                self._group_map[uuid] = gid
                self._group_ref_count[gid] += 1
                new_group = False
                break
        if new_group:
            gid = str(uuid4())
            self._groups.append({"uuid": gid, "lon": ilon, "lat": ilat})
            self._group_map[uuid] = gid
            self._group_ref_count[gid] = 1

    def get_groups(self):
        return copy.deepcopy(self._groups)

    def get_available_units(self):
        return copy.deepcopy(self._db)

    def get_in_use_units(self):
        return copy.deepcopy(self._in_use)

    def rent_item(self, uuid):
        for i, item in enumerate(self._db):
            if item["uuid"] == uuid:
                rented_item = self._db.pop(i)
                self._in_use.append(rented_item)
                
                # Update aggregation
                gid = self._group_map.get(uuid)
                if gid:
                    self._group_ref_count[gid] -= 1
                    if self._group_ref_count[gid] == 0:
                        self._groups = [g for g in self._groups if g["uuid"] != gid]
                        self._group_ref_count.pop(gid)
                    self._group_map.pop(uuid)
                return rented_item
        return None

    def return_item(self, uuid, lat, lon):
        for i, item in enumerate(self._in_use):
            if item["uuid"] == uuid:
                item = self._in_use.pop(i)
                item["lat"] = lat
                item["lon"] = lon
                self.add_item(item)
                return item
        return None

    def log_state(self, current_time):
        self.history.append({
            "time": current_time,
            "available_units": self.get_groups(), # Log aggregated groups
            "real_available_units": self.get_available_units(), # For debugging/reference
            "in_use_units": self.get_in_use_units()
        })

# Global state
DB = DataBase()
CURRENT_TIME = 0
PORT = 8000 #

class ElectricKickbikeGenerator:
    def generate(self):
        return {
            "uuid": str(uuid4()),
            "lat": random.uniform(-0.25, 0.25),
            "lon": random.uniform(-0.25, 0.25)
        }

class RentalSimulatorAggregateHandler(BaseHTTPRequestHandler):
    def _send_json_response(self, status_code, data):
        content = json.dumps(data)
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content.encode())

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/api/stockholm":
            self.get_stockholm()
        elif parsed_path.path == "/api/stockholm/statistics":
            self.get_stockholm_statistics()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed_path = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            data = {}

        if parsed_path.path == "/api/rent":
            self.post_rent(data)
        elif parsed_path.path == "/api/return":
            self.post_return(data)
        elif parsed_path.path == "/api/advance_time":
            self.post_advance_time(data)
        else:
            self.send_error(404, "Not Found")

    def post_advance_time(self, data):
        global CURRENT_TIME
        amount = data.get("amount", 1)
        CURRENT_TIME += amount
        DB.log_state(CURRENT_TIME)
        self._send_json_response(200, {"status": "success", "new_time": CURRENT_TIME})

    def get_stockholm(self):
        response = {
            "time": CURRENT_TIME,
            "available_units": DB.get_groups() # Returns aggregated groups
        }
        self._send_json_response(200, response)

    def get_stockholm_statistics(self):
        self._send_json_response(200, DB.history)

    def post_rent(self, data):
        scooter_uuid = data.get("uuid")
        if not scooter_uuid:
            self._send_json_response(400, {"error": "Missing uuid"})
            return

        rented_scooter = DB.rent_item(scooter_uuid)
        if rented_scooter:
            DB.log_state(CURRENT_TIME)
            self._send_json_response(200, {"status": "success", "scooter": rented_scooter})
        else:
            self._send_json_response(404, {"error": "Scooter not available or not found"})

    def post_return(self, data):
        scooter_uuid = data.get("uuid")
        lat = data.get("lat")
        lon = data.get("lon")

        if not all([scooter_uuid, lat is not None, lon is not None]):
            self._send_json_response(400, {"error": "Missing uuid, lat, or lon"})
            return

        returned_scooter = DB.return_item(scooter_uuid, lat, lon)
        if returned_scooter:
            DB.log_state(CURRENT_TIME)
            self._send_json_response(200, {"status": "success", "scooter": returned_scooter})
        else:
            self._send_json_response(404, {"error": "Scooter not rented or not found"})

def run(server_class=HTTPServer, handler_class=RentalSimulatorAggregateHandler):
    server_address = ('', PORT)
    httpd = server_class(server_address, handler_class)
    print(f"Rental Simulator (Aggregate) listening on port: {PORT}")
    
    # Initialize DB with some scooters
    ekb = ElectricKickbikeGenerator()
    for _ in range(15):
        DB.add_item(ekb.generate())
    
    DB.log_state(CURRENT_TIME) # Initial State logged
        
    httpd.serve_forever()

if __name__ == "__main__":
    run()
