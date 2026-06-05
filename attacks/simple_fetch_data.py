import requests
import json

BASE_URL = "http://localhost:8000/api"

def fetch_data():
    try:
        response = requests.get(f"{BASE_URL}/stockholm/statistics")
        if response.status_code == 200:
            data = response.json()
            with open("response.json", "w") as f:
                json.dump(data, f, indent=4)
            print("Data saved to response.json")
            return data
        else:
            print(f"Failed to fetch data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

if __name__ == "__main__":
    fetch_data()