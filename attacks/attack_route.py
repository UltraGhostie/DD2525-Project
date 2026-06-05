import requests
import time
import pandas as pd

# Configuration
API_URL = "http://localhost:8000/api/stockholm"
DURATION_MINUTES = 1
DURATION_SECONDS = DURATION_MINUTES * 60
POLL_INTERVAL = 0.1  # How often to ping the server in seconds


def collect_scooter_data():
    print(f"Starting scooter data collection for {DURATION_MINUTES} minutes")
    start_time = time.time()
    data_records = []

    # Run loop until duration over
    while time.time() - start_time < DURATION_SECONDS:
        try:
            response = requests.get(API_URL)

            if response.status_code == 200:
                data = response.json()
                server_time = data.get("time", 0)
                available_units = data.get("available_units", [])

                # Register each scooter's position at the current time step
                for unit in available_units:
                    data_records.append({
                        "uuid": unit["uuid"],
                        "server_time": server_time,
                        "lat": unit["lat"],
                        "lon": unit["lon"]
                    })

        except requests.exceptions.ConnectionError:
            print("Failed to connect to the server.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

        # Wait before the next request
        time.sleep(POLL_INTERVAL)

    print("Saving Data")
    save_to_excel(data_records)


def save_to_excel(records):
    if not records:
        print("No data was collected.")
        return

    # Convert the list of records into a pandas DataFrame
    df = pd.DataFrame(records)

    # Sort the data by UUID first, then by time.
    df = df.sort_values(by=["uuid", "server_time"])

    # Output to an Excel file
    filename = "../scooter_position_chain.xlsx"
    df.to_excel(filename, index=False)

    print(f"Successfully saved tracking data for {df['uuid'].nunique()} scooters to {filename}")


if __name__ == "__main__":
    collect_scooter_data()