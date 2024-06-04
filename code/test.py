import matplotlib.pyplot as plt

# Sample latitude and longitude data
latitude = [36.7134, 36.7134, 36.7134, 36.7134, 36.7134, 36.7134, 36.7134]
longitude = [-4.426812, -4.426812, -4.426812, -4.426812, -4.426812, -4.426812, -4.426812]

# Plot the coordinates
plt.figure(figsize=(10, 6))
plt.scatter(longitude, latitude, color='blue', marker='o')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title('Geographic Coordinates')
plt.grid(True)
plt.show()
