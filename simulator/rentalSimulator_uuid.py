from http.server import BaseHTTPRequestHandler, HTTPServer
from uuid import uuid4
import random
import json
from urllib.parse import urlparse, parse_qs
import copy

import time

DB = []
IN_USE = {}  
DB_HISTORY = []
CURRENT_TIME = 0
PORT = 8000

def get_current_time():
    return CURRENT_TIME

def log_state():
    global DB_HISTORY, DB, IN_USE, CURRENT_TIME
    # In this version, we log the public_uuid that is visible at this time
    DB_HISTORY.append({
        "time": CURRENT_TIME,
        "available_units": copy.deepcopy([
            {"uuid": s["public_uuid"], "lat": s["lat"], "lon": s["lon"]} for s in DB
        ]),
        "in_use_units": copy.deepcopy([
            {"uuid": s["public_uuid"], "lat": s["lat"], "lon": s["lon"]} for s in IN_USE.values()
        ])
    })

class ElectricKickbikeGenerator:
    def generate(self):
        return {
            "private_uuid": str(uuid4()),
            "public_uuid": str(uuid4()),
            "lat": random.uniform(-0.25, 0.25), 
            "lon": random.uniform(-0.25, 0.25)
        }

class RentalSimulatorHandler(BaseHTTPRequestHandler):
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
        log_state()
        self._send_json_response(200, {"status": "success", "new_time": CURRENT_TIME})

    def get_stockholm(self):
        # Only expose public_uuid
        available_units = [
            {"uuid": s["public_uuid"], "lat": s["lat"], "lon": s["lon"]} for s in DB
        ]
        response = {
            "time": get_current_time(),
            "available_units": available_units
        }
        self._send_json_response(200, response)

    def get_stockholm_statistics(self):
        self._send_json_response(200, DB_HISTORY)

    def post_rent(self, data):
        global DB, IN_USE
        scooter_uuid = data.get("uuid") # This is the public_uuid
        if not scooter_uuid:
            self._send_json_response(400, {"error": "Missing uuid"})
            return

        for i, scooter in enumerate(DB):
            if scooter["public_uuid"] == scooter_uuid:
                rented_scooter = DB.pop(i)
                # We use private_uuid as key in IN_USE to keep track of the physical unit
                IN_USE[rented_scooter["private_uuid"]] = rented_scooter
                log_state()
                # Return the scooter with its current public_uuid
                response_scooter = {
                    "uuid": rented_scooter["public_uuid"],
                    "lat": rented_scooter["lat"],
                    "lon": rented_scooter["lon"]
                }
                self._send_json_response(200, {"status": "success", "scooter": response_scooter})
                return
        
        self._send_json_response(404, {"error": "Scooter not available or not found"})

    def post_return(self, data):
        global DB, IN_USE
        scooter_uuid = data.get("uuid") # public_uuid used for renting
        lat = data.get("lat")
        lon = data.get("lon")

        if not all([scooter_uuid, lat is not None, lon is not None]):
            self._send_json_response(400, {"error": "Missing uuid, lat, or lon"})
            return

        # Find the scooter in IN_USE by its public_uuid
        target_private_uuid = None
        for priv_uuid, scooter in IN_USE.items():
            if scooter["public_uuid"] == scooter_uuid:
                target_private_uuid = priv_uuid
                break

        if target_private_uuid:
            scooter = IN_USE.pop(target_private_uuid)
            scooter["lat"] = lat
            scooter["lon"] = lon
            
            # Generate a new public UUID after each use
            scooter["public_uuid"] = str(uuid4())
            
            DB.append(scooter)
            log_state()
            
            response_scooter = {
                "uuid": scooter["public_uuid"], # Return the new public uuid
                "lat": scooter["lat"],
                "lon": scooter["lon"]
            }
            self._send_json_response(200, {"status": "success", "scooter": response_scooter})
        else:
            self._send_json_response(404, {"error": "Scooter not rented or not found"})

def run(server_class=HTTPServer, handler_class=RentalSimulatorHandler):
    server_address = ('', PORT)
    httpd = server_class(server_address, handler_class)
    print(f"Rental Simulator with UUID Rotation listening on port: {PORT}")
    
    # Initialize DB with some scooters
    ekb = ElectricKickbikeGenerator()
    for _ in range(15):
        DB.append(ekb.generate())
    
    log_state() # Initial State logged
        
    httpd.serve_forever()

if __name__ == "__main__":
    run()
