"""
Real-World Usage Examples for MQTT Schema System

This file demonstrates practical use cases:
1. Smart Home Temperature Control System
2. Industrial Sensor Network
3. Vehicle Fleet Tracking
4. Health Monitoring System
"""

import time
import logging
from typing import Dict, List
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from base_types import MqttMessage
    from mqtt import Mqtt, Topic
    from SOFTWARE.communication.Float.schema.config_manager import MQTTConfigManager
    from SOFTWARE.communication.Float.schema.mqtt_schema_adapter import MessageSchema_to_MqttMessage_Adapter
    from SOFTWARE.communication.Float.schema.mqtt_schema_types import MQTTBrokerConfig, AllTopicsSchema, MessageSchema, TopicSchema
    from SOFTWARE.communication.Float.schema.abstract_schema_configuration.abstract_schema import FieldSchema
except ImportError as e:
    logger.error(f"Import error: {e}")
    raise


class SmartHomeThermostat:
    """Example 1: Smart Home Temperature Control"""
    
    def __init__(self, mqtt_connection: Mqtt):
        self.mqtt = mqtt_connection
        self.config = self._create_config()
        self.rooms = {}
        
    def _create_config(self) -> MQTTConfigManager:
        """Create configuration for smart home system"""
        config = MQTTConfigManager()
        
        # Temperature sensor topic
        temp_schema = MessageSchema(
            name="TemperatureSensor",
            fields=[
                FieldSchema.string(name="room", value="living_room"),
                FieldSchema.float_field(name="temperature", value=22.0, min_value=-10.0, max_value=50.0),
                FieldSchema.float_field(name="humidity", value=45.0, min_value=0.0, max_value=100.0),
                FieldSchema.integer(name="timestamp", value=0)
            ]
        )
        config.add_topic(TopicSchema(name="home/sensors/temperature", message_schema=temp_schema))
        
        # Thermostat control topic
        control_schema = MessageSchema(
            name="ThermostatControl",
            fields=[
                FieldSchema.string(name="room", value="living_room"),
                FieldSchema.float_field(name="target_temp", value=21.0, min_value=15.0, max_value=30.0),
                FieldSchema.string(name="mode", value="auto", 
                                 allowed_values=["auto", "heat", "cool", "off"]),
                FieldSchema.boolean(name="fan_on", value=False)
            ]
        )
        config.add_topic(TopicSchema(name="home/thermostat/control", message_schema=control_schema))
        
        # Alert topic
        alert_schema = MessageSchema(
            name="HomeAlert",
            fields=[
                FieldSchema.string(name="room", value=""),
                FieldSchema.string(name="alert_type", value="temperature", 
                                 allowed_values=["temperature", "humidity", "system"]),
                FieldSchema.string(name="severity", value="info",
                                 allowed_values=["info", "warning", "critical"]),
                FieldSchema.string(name="message", value="")
            ]
        )
        config.add_topic(TopicSchema(name="home/alerts", message_schema=alert_schema))
        
        return config
    
    def monitor_room(self, room_name: str):
        """Start monitoring a room"""
        # Get temperature sensor handler
        temp_schema = self.config.get_message_schema("home/sensors/temperature")
        temp_handler = MessageSchema_to_MqttMessage_Adapter(temp_schema)
        
        # Subscribe to temperature updates
        temp_topic = Topic("home/sensors/temperature", self.mqtt)
        temp_topic.subscribe(temp_handler)
        
        self.rooms[room_name] = {
            'temp_handler': temp_handler,
            'temp_topic': temp_topic
        }
        
        logger.info(f"Started monitoring {room_name}")
    
    def publish_temperature(self, room: str, temp: float, humidity: float):
        """Publish temperature reading"""
        temp_schema = self.config.get_message_schema("home/sensors/temperature")
        publisher = MessageSchema_to_MqttMessage_Adapter(temp_schema)
        
        publisher.set_variable("room", room)
        publisher.set_variable("temperature", temp)
        publisher.set_variable("humidity", humidity)
        publisher.set_variable("timestamp", int(time.time()))
        
        topic = Topic("home/sensors/temperature", self.mqtt)
        topic.publish(publisher.encode())
        
        logger.info(f"Published: {room} temp={temp}°C, humidity={humidity}%")
    
    def set_thermostat(self, room: str, target_temp: float, mode: str = "auto"):
        """Set thermostat for a room"""
        control_schema = self.config.get_message_schema("home/thermostat/control")
        publisher = MessageSchema_to_MqttMessage_Adapter(control_schema)
        
        publisher.set_variable("room", room)
        publisher.set_variable("target_temp", target_temp)
        publisher.set_variable("mode", mode)
        publisher.set_variable("fan_on", mode != "off")
        
        topic = Topic("home/thermostat/control", self.mqtt)
        topic.publish(publisher.encode())
        
        logger.info(f"Set thermostat: {room} to {target_temp}°C, mode={mode}")
    
    def send_alert(self, room: str, alert_type: str, severity: str, message: str):
        """Send an alert"""
        alert_schema = self.config.get_message_schema("home/alerts")
        publisher = MessageSchema_to_MqttMessage_Adapter(alert_schema)
        
        publisher.set_variable("room", room)
        publisher.set_variable("alert_type", alert_type)
        publisher.set_variable("severity", severity)
        publisher.set_variable("message", message)
        
        topic = Topic("home/alerts", self.mqtt)
        topic.publish(publisher.encode())
        
        logger.info(f"Alert [{severity}] from {room}: {message}")


class IndustrialSensorNetwork:
    """Example 2: Industrial Sensor Network"""
    
    def __init__(self, mqtt_connection: Mqtt):
        self.mqtt = mqtt_connection
        self.config = self._create_config()
        
    def _create_config(self) -> MQTTConfigManager:
        """Create industrial sensor configuration"""
        config = MQTTConfigManager()
        
        # Pressure sensor
        pressure_schema = MessageSchema(
            name="PressureSensor",
            fields=[
                FieldSchema.string(name="sensor_id", value=""),
                FieldSchema.string(name="location", value=""),
                FieldSchema.float_field(name="pressure_bar", value=0.0, min_value=0.0, max_value=100.0),
                FieldSchema.float_field(name="temperature_c", value=0.0),
                FieldSchema.integer(name="timestamp", value=0),
                FieldSchema.string(name="status", value="normal", 
                                 allowed_values=["normal", "warning", "critical", "fault"])
            ]
        )
        config.add_topic(TopicSchema(name="industrial/sensors/pressure", message_schema=pressure_schema))
        
        # Flow meter
        flow_schema = MessageSchema(
            name="FlowMeter",
            fields=[
                FieldSchema.string(name="sensor_id", value=""),
                FieldSchema.string(name="pipeline", value=""),
                FieldSchema.float_field(name="flow_rate_lpm", value=0.0, min_value=0.0),
                FieldSchema.float_field(name="total_volume_liters", value=0.0),
                FieldSchema.integer(name="timestamp", value=0)
            ]
        )
        config.add_topic(TopicSchema(name="industrial/sensors/flow", message_schema=flow_schema))
        
        # Vibration sensor
        vibration_schema = MessageSchema(
            name="VibrationSensor",
            fields=[
                FieldSchema.string(name="sensor_id", value=""),
                FieldSchema.string(name="equipment", value=""),
                FieldSchema.float_field(name="vibration_mm_s", value=0.0),
                FieldSchema.float_field(name="frequency_hz", value=0.0),
                FieldSchema.integer(name="timestamp", value=0),
                FieldSchema.boolean(name="alarm", value=False)
            ]
        )
        config.add_topic(TopicSchema(name="industrial/sensors/vibration", message_schema=vibration_schema))
        
        return config
    
    def publish_pressure_reading(self, sensor_id: str, location: str, pressure: float, temp: float):
        """Publish pressure sensor reading"""
        schema = self.config.get_message_schema("industrial/sensors/pressure")
        publisher = MessageSchema_to_MqttMessage_Adapter(schema)
        
        # Determine status based on pressure
        status = "normal"
        if pressure > 80:
            status = "critical"
        elif pressure > 60:
            status = "warning"
        
        publisher.set_variable("sensor_id", sensor_id)
        publisher.set_variable("location", location)
        publisher.set_variable("pressure_bar", pressure)
        publisher.set_variable("temperature_c", temp)
        publisher.set_variable("timestamp", int(time.time()))
        publisher.set_variable("status", status)
        
        topic = Topic("industrial/sensors/pressure", self.mqtt)
        topic.publish(publisher.encode())
        
        logger.info(f"Pressure: {sensor_id} @ {location}: {pressure} bar [{status}]")
    
    def publish_flow_reading(self, sensor_id: str, pipeline: str, flow_rate: float, total_volume: float):
        """Publish flow meter reading"""
        schema = self.config.get_message_schema("industrial/sensors/flow")
        publisher = MessageSchema_to_MqttMessage_Adapter(schema)
        
        publisher.set_variable("sensor_id", sensor_id)
        publisher.set_variable("pipeline", pipeline)
        publisher.set_variable("flow_rate_lpm", flow_rate)
        publisher.set_variable("total_volume_liters", total_volume)
        publisher.set_variable("timestamp", int(time.time()))
        
        topic = Topic("industrial/sensors/flow", self.mqtt)
        topic.publish(publisher.encode())
        
        logger.info(f"Flow: {sensor_id} @ {pipeline}: {flow_rate} L/min")


class VehicleFleetTracker:
    """Example 3: Vehicle Fleet Tracking System"""
    
    def __init__(self, mqtt_connection: Mqtt):
        self.mqtt = mqtt_connection
        self.config = self._create_config()
        
    def _create_config(self) -> MQTTConfigManager:
        """Create fleet tracking configuration"""
        config = MQTTConfigManager()
        
        # GPS location
        gps_schema = MessageSchema(
            name="VehicleGPS",
            fields=[
                FieldSchema.string(name="vehicle_id", value=""),
                FieldSchema.float_field(name="latitude", value=0.0, min_value=-90.0, max_value=90.0),
                FieldSchema.float_field(name="longitude", value=0.0, min_value=-180.0, max_value=180.0),
                FieldSchema.float_field(name="speed_kmh", value=0.0, min_value=0.0),
                FieldSchema.float_field(name="heading_degrees", value=0.0, min_value=0.0, max_value=360.0),
                FieldSchema.integer(name="timestamp", value=0)
            ]
        )
        config.add_topic(TopicSchema(name="fleet/gps", message_schema=gps_schema))
        
        # Vehicle status
        status_schema = MessageSchema(
            name="VehicleStatus",
            fields=[
                FieldSchema.string(name="vehicle_id", value=""),
                FieldSchema.string(name="engine_status", value="off",
                                 allowed_values=["off", "idle", "running"]),
                FieldSchema.integer(name="fuel_percent", value=100, min_value=0, max_value=100),
                FieldSchema.float_field(name="engine_temp_c", value=0.0),
                FieldSchema.integer(name="odometer_km", value=0),
                FieldSchema.boolean(name="maintenance_due", value=False)
            ]
        )
        config.add_topic(TopicSchema(name="fleet/status", message_schema=status_schema))
        
        # Driver info
        driver_schema = MessageSchema(
            name="DriverInfo",
            fields=[
                FieldSchema.string(name="vehicle_id", value=""),
                FieldSchema.string(name="driver_id", value=""),
                FieldSchema.string(name="driver_name", value=""),
                FieldSchema.string(name="shift_status", value="off_duty",
                                 allowed_values=["off_duty", "on_duty", "driving", "break"]),
                FieldSchema.integer(name="hours_driven", value=0, min_value=0)
            ]
        )
        config.add_topic(TopicSchema(name="fleet/driver", message_schema=driver_schema))
        
        return config
    
    def update_gps(self, vehicle_id: str, lat: float, lon: float, speed: float, heading: float):
        """Update vehicle GPS location"""
        schema = self.config.get_message_schema("fleet/gps")
        publisher = MessageSchema_to_MqttMessage_Adapter(schema)
        
        publisher.set_variable("vehicle_id", vehicle_id)
        publisher.set_variable("latitude", lat)
        publisher.set_variable("longitude", lon)
        publisher.set_variable("speed_kmh", speed)
        publisher.set_variable("heading_degrees", heading)
        publisher.set_variable("timestamp", int(time.time()))
        
        topic = Topic("fleet/gps", self.mqtt)
        topic.publish(publisher.encode())
        
        logger.info(f"GPS: {vehicle_id} @ ({lat}, {lon}), {speed} km/h")
    
    def update_vehicle_status(self, vehicle_id: str, engine_status: str, fuel: int, 
                             engine_temp: float, odometer: int):
        """Update vehicle status"""
        schema = self.config.get_message_schema("fleet/status")
        publisher = MessageSchema_to_MqttMessage_Adapter(schema)
        
        # Check if maintenance is due (every 10000 km)
        maintenance_due = (odometer % 10000) < 100
        
        publisher.set_variable("vehicle_id", vehicle_id)
        publisher.set_variable("engine_status", engine_status)
        publisher.set_variable("fuel_percent", fuel)
        publisher.set_variable("engine_temp_c", engine_temp)
        publisher.set_variable("odometer_km", odometer)
        publisher.set_variable("maintenance_due", maintenance_due)
        
        topic = Topic("fleet/status", self.mqtt)
        topic.publish(publisher.encode())
        
        logger.info(f"Status: {vehicle_id} - {engine_status}, fuel={fuel}%, odo={odometer}km")


def demo_smart_home():
    """Demonstrate smart home system"""
    logger.info("\n" + "="*70)
    logger.info("DEMO 1: Smart Home Temperature Control")
    logger.info("="*70)
    
    mqtt = Mqtt(address='localhost', port=1883)
    home = SmartHomeThermostat(mqtt)
    
    # Monitor rooms
    home.monitor_room("living_room")
    home.monitor_room("bedroom")
    
    time.sleep(2)
    
    # Simulate temperature readings
    rooms_data = [
        ("living_room", 23.5, 48.0),
        ("bedroom", 21.0, 45.0),
        ("kitchen", 24.0, 52.0)
    ]
    
    for room, temp, humidity in rooms_data:
        home.publish_temperature(room, temp, humidity)
        time.sleep(0.5)
    
    # Adjust thermostats
    home.set_thermostat("living_room", 22.0, "cool")
    time.sleep(0.5)
    home.set_thermostat("bedroom", 20.0, "auto")
    time.sleep(0.5)
    
    # Send alerts
    home.send_alert("living_room", "temperature", "warning", "Temperature above target")
    time.sleep(0.5)
    
    # Save configuration
    home.config.save_config("/tmp/smart_home_config.yaml")
    logger.info("Configuration saved to /tmp/smart_home_config.yaml")
    
    time.sleep(2)
    mqtt.cleanup()
    
    logger.info("Smart Home demo completed\n")


def demo_industrial_sensors():
    """Demonstrate industrial sensor network"""
    logger.info("\n" + "="*70)
    logger.info("DEMO 2: Industrial Sensor Network")
    logger.info("="*70)
    
    mqtt = Mqtt(address='localhost', port=1883)
    industrial = IndustrialSensorNetwork(mqtt)
    
    time.sleep(2)
    
    # Simulate sensor readings
    import random
    
    for i in range(5):
        # Pressure sensors
        industrial.publish_pressure_reading(
            sensor_id=f"PS-{i+1:03d}",
            location=f"Tank-{chr(65+i)}",
            pressure=random.uniform(20, 90),
            temp=random.uniform(15, 35)
        )
        time.sleep(0.3)
        
        # Flow meters
        industrial.publish_flow_reading(
            sensor_id=f"FM-{i+1:03d}",
            pipeline=f"Line-{i+1}",
            flow_rate=random.uniform(10, 200),
            total_volume=random.uniform(1000, 50000)
        )
        time.sleep(0.3)
    
    # Save configuration
    industrial.config.save_config("/tmp/industrial_config.yaml")
    logger.info("Configuration saved to /tmp/industrial_config.yaml")
    
    time.sleep(2)
    mqtt.cleanup()
    
    logger.info("Industrial Sensors demo completed\n")


def demo_vehicle_fleet():
    """Demonstrate vehicle fleet tracking"""
    logger.info("\n" + "="*70)
    logger.info("DEMO 3: Vehicle Fleet Tracking")
    logger.info("="*70)
    
    mqtt = Mqtt(address='localhost', port=1883)
    fleet = VehicleFleetTracker(mqtt)
    
    time.sleep(2)
    
    # Simulate vehicle data
    vehicles = [
        {"id": "VEH-001", "lat": 40.7128, "lon": -74.0060, "speed": 45},  # New York
        {"id": "VEH-002", "lat": 34.0522, "lon": -118.2437, "speed": 60}, # Los Angeles
        {"id": "VEH-003", "lat": 41.8781, "lon": -87.6298, "speed": 0}    # Chicago (stopped)
    ]
    
    for i, vehicle in enumerate(vehicles):
        # Update GPS
        fleet.update_gps(
            vehicle_id=vehicle["id"],
            lat=vehicle["lat"],
            lon=vehicle["lon"],
            speed=vehicle["speed"],
            heading=float((i * 90) % 360)
        )
        time.sleep(0.5)
        
        # Update status
        engine_status = "running" if vehicle["speed"] > 0 else "idle"
        fleet.update_vehicle_status(
            vehicle_id=vehicle["id"],
            engine_status=engine_status,
            fuel=random.randint(30, 90),
            engine_temp=random.uniform(70, 95),
            odometer=random.randint(5000, 50000)
        )
        time.sleep(0.5)
    
    # Save configuration
    fleet.config.save_config("/tmp/fleet_config.yaml")
    logger.info("Configuration saved to /tmp/fleet_config.yaml")
    
    time.sleep(2)
    mqtt.cleanup()
    
    logger.info("Vehicle Fleet demo completed\n")


def main():
    """Run all demonstrations"""
    logger.info("\n" + "="*70)
    logger.info("MQTT SCHEMA SYSTEM - REAL-WORLD USAGE EXAMPLES")
    logger.info("="*70)
    
    try:
        demo_smart_home()
        demo_industrial_sensors()
        demo_vehicle_fleet()
        
        logger.info("\n" + "="*70)
        logger.info("All demonstrations completed successfully!")
        logger.info("Configuration files saved to /tmp/")
        logger.info("="*70)
        
    except KeyboardInterrupt:
        logger.info("\nDemonstrations interrupted by user")
    except Exception as e:
        logger.error(f"Error during demonstrations: {e}")
        raise


if __name__ == "__main__":
    main()
