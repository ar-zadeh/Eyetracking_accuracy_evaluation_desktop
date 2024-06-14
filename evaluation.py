import tkinter as tk
import time
import socket
import re
import math
import numpy as np
import csv
import os

# Define the file name
filename = 'eye_tracking_results_30.csv'


# Eye-tracking data collection setup
HOST = '127.0.0.1'
PORT = 4242
pattern = re.compile(r'BPOGX="([^"]+)" BPOGY="([^"]+)"')

# Function to calculate Euclidean distance
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

# Function to update the position of the dot and collect data
def update_position(x, y, wait_time, duration, sock, distances):
    global data_loss
    canvas.coords(circle, x - 10, y - 10, x + 10, y + 10)
    root.update()
    current = time.time()
    # Wait before collecting data
    while time.time() < current+wait_time:
        data = sock.recv(1024).decode('utf-8')

    x = 1920 -x
    print(f'at {x} amd {y}','=======================================================')

    # Collect and compare data
    end_time = time.time() + duration
    while time.time() < end_time:
        data = sock.recv(1024).decode('utf-8')
        matches = pattern.findall(data)
        for match in matches:
            bpogx, bpogy = match
            bpogx = 1920-int(float(bpogx) * 1920)
            bpogy = int(float(bpogy) * 1080)
            print(bpogx,bpogy)
            if bpogx == 0 or bpogx == 1920 or bpogx == 0 or bpogy ==1080:
                print('invalid')
                data_loss.append(1)
            else:
                distance = calculate_distance(bpogx, bpogy, x, y)
                distances.append(distance)

# Create a blank Tkinter window
root = tk.Tk()
root.attributes('-fullscreen', True)  # Set the window to fullscreen mode
canvas = tk.Canvas(root, width=root.winfo_screenwidth(), height=root.winfo_screenheight(), bg='black', highlightthickness=0)
root.configure(bg='black')

canvas.pack()

# Initial position of the white dot (center of the screen)
circle = canvas.create_oval(960 - 10, 540 - 10, 960 + 10, 540 + 10, fill='white')

# Connect to the Gazepoint server
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((HOST, PORT))
    sock.sendall(b'<SET ID="ENABLE_SEND_DATA" STATE="1" />\r\n')
    sock.sendall(b'<SET ID="ENABLE_SEND_POG_BEST" STATE="1" />\r\n')
    time.sleep(1)  # Allow some time for data to start generating
    point_distances = {
        'center': [],
        'top_left': [],
        'top_right': [],
        'bottom_left': [],
        'bottom_right': []
    }

    distances = []
    data_loss = []
    # Update positions and collect data
    update_position(960, 540, 2, 1, sock, point_distances['center'])  # Center
    update_position(40, 40, 2, 1, sock, point_distances['top_left'])  # Top-left
    update_position(1880, 40, 2, 1, sock, point_distances['top_right'])  # Top-right
    update_position(40, 1040, 2, 1, sock, point_distances['bottom_left'])  # Bottom-left
    update_position(1880, 1040, 2, 1, sock, point_distances['bottom_right'])  # Bottom-right

    # Command to stop data stream
    sock.sendall(b'<SET ID="ENABLE_SEND_DATA" STATE="0" />\r\n')

# Close the Tkinter window
root.destroy()
results = {}
for point, distances in point_distances.items():
    results[point] = {
        'average': np.average(distances) if distances else 0,
        'std_dev': np.std(distances) if distances else 0
    }

# Combine all distances to calculate overall metrics
all_distances = [distance for distances in point_distances.values() for distance in distances]
overall_average = np.average(all_distances) if all_distances else 0
overall_std_dev = np.std(all_distances) if all_distances else 0

# Add overall metrics to the results dictionary
results['overall'] = {
    'average': overall_average,
    'std_dev': overall_std_dev
}

# Append the results to the CSV file
if not os.path.exists(filename):
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        # Write the headers
        headers = []
        for point in ['P1', 'P2', 'P3', 'P4', 'P5', 'Total']:
            headers.extend([f'Average_{point}', f'STD_{point}'])
        writer.writerow(headers)

# Prepare data row
data_row = []
for point in ['center', 'top_left', 'top_right', 'bottom_left', 'bottom_right']:
    data_row.extend([results[point]['average'], results[point]['std_dev']])
# Add overall metrics
data_row.extend([overall_average, overall_std_dev])

# Write the data
with open(filename, 'a', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(data_row)
