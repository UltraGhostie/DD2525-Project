import matplotlib.pyplot as plt
import numpy as np
import random

def main():
    # Set the range
    min_val, max_val = -0.25, 0.25
    
    plt.figure(figsize=(10, 10))
    
    # 3 blue dots (Rented)
    rented_points = [
        (random.uniform(min_val * 0.8, max_val * 0.8), random.uniform(min_val * 0.8, max_val * 0.8))
        for _ in range(3)
    ]
    
    # 3 X's (returned)
    returned_points = [
        (random.uniform(min_val * 0.8, max_val * 0.8), random.uniform(min_val * 0.8, max_val * 0.8))
        for _ in range(3)
    ]
    
    # Plot Rented points
    rx, ry = zip(*rented_points)
    plt.scatter(rx, ry, c='blue', label='(Rented)', s=100, marker='o', edgecolors='black')
    
    # Plot Returned points
    tx, ty = zip(*returned_points)
    plt.scatter(tx, ty, c='red', label='(returned)', s=100, marker='x')
    
    # For each blue dot, make a hypothetical minimum and maximum circle 
    # where only one X belongs inside each span. (Only demonstrating)
    colors = ['lightblue', 'lightgreen', 'pink']
    for i, rented in enumerate(rented_points):
        # Calculate distances to all returned points
        distances = []
        for returned in returned_points:
            dist = np.sqrt((rented[0] - returned[0])**2 + (rented[1] - returned[1])**2)
            distances.append(dist)
        
        sorted_distances = sorted(distances)
        
        target_dist = distances[i]
        
        # Find the neighbors of target_dist in the sorted list
        idx = sorted_distances.index(target_dist)
        
        if idx == 0:
            min_r = target_dist * 0.8 # just pretending
        else:
            min_r = (sorted_distances[idx-1] + target_dist) / 2 # if conflicting with another value
            
        if idx == len(sorted_distances) - 1:
            max_r = target_dist * 1.2
        else:
            max_r = (target_dist + sorted_distances[idx+1]) / 2
            
        # Draw the circles
        circle_min = plt.Circle(rented, min_r, color=colors[i], fill=False, linestyle='--', alpha=0.5)
        circle_max = plt.Circle(rented, max_r, color=colors[i], fill=False, linestyle='-', alpha=0.5)
        plt.gca().add_patch(circle_min)
        plt.gca().add_patch(circle_max)
        
        # Add a light fill between them
        theta = np.linspace(0, 2*np.pi, 100)
        x_min = rented[0] + min_r * np.cos(theta)
        y_min = rented[1] + min_r * np.sin(theta)
        x_max = rented[0] + max_r * np.cos(theta)
        y_max = rented[1] + max_r * np.sin(theta)
        # plt.fill(np.append(x_min, x_max[::-1]), np.append(y_min, y_max[::-1]), color=colors[i], alpha=0.1)
        plt.fill(np.concatenate([x_min, x_max[::-1]]), np.concatenate([y_min, y_max[::-1]]), color=colors[i], alpha=0.1)

    plt.xlim(min_val, max_val)
    plt.ylim(min_val, max_val)
    plt.title("Example: estimating the correlated location of a rented scooter and its return")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend()
    plt.grid(True)
    plt.savefig("graph_example.png")
    print("Graph saved as graph_example.png")

if __name__ == "__main__":
    main()
