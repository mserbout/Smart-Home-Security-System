# Smart Home Security System

## Title
Smart Home Security System

## Scope of the Solution
The system will monitor and control home security features. The functionalities include:

1. **Temperature and Humidity Monitoring:** Using the DHT sensor, the system can monitor the temperature and humidity levels in your home.
2. **Motion Detection:** The motion sensor can detect any movement in your home. If any movement is detected when the system is armed, it can trigger an alarm or notification.
3. **Light Control:** The LEDs can be used to indicate the status of the system or act as a visual alarm. They can also be controlled remotely.
4. **Remote Access:** Using Bluetooth, the system can be controlled remotely from a smartphone or computer.

## Hardware Elements and Communication Technologies
- Arduino: Acts as the main controller of the system.
- ESP Module: Provides Wi-Fi connectivity to connect the system to the internet.
- DHT Sensor: Monitors temperature and humidity.
- Motion Sensor: Detects movement.
- LEDs: Provide visual indicators or alarms.
- Bluetooth Module: Allows for remote control of the system.

## Note
- If the temperature or humidity value is reached a value specify, a notification will also be sent like in a telegram.
- Show the status of the house on Display data (we will ask in exist in biblioteca).

## Data Visualization

### Real-time Monitoring:
- Display the current temperature and humidity readings in a visually appealing format, such as a line graph or gauge.
- Show the status of the motion sensor, indicating whether motion is currently detected or not.
- Use color-coded indicators or icons to quickly convey the status of each parameter (e.g., green for normal, red for alert).

### Historical Data Analysis:
- Provide historical charts or graphs showing trends in temperature and humidity over time. Users can select different time ranges (e.g., hourly, daily, weekly) for analysis.
- Plot motion events on a timeline to visualize when movement was detected and for how long.
- Include statistical information such as average temperature, highest humidity level, or frequency of motion events over a specified period.

### Customizable Alerts and Notifications:
- Allow users to set custom thresholds for temperature, humidity, and motion detection. When these thresholds are exceeded, trigger alerts and notifications to inform the user.
- Provide options for users to choose their preferred notification methods (e.g., push notifications, email alerts, SMS messages).

### User Preferences and Settings:
- Allow users to customize the dashboard layout, choose which data parameters to display, and adjust visualization settings according to their preferences.
- Provide options for users to export or download historical data for further analysis or record-keeping purposes.
