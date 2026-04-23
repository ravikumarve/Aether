"""
AETHER MQTT Client
Communication layer for inter-agent messaging using MQTT protocol.
"""

import json
import logging
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MQTTMessage:
    """Represents an MQTT message with metadata."""
    topic: str
    payload: Dict[str, Any]
    timestamp: datetime
    qos: int = 0
    retain: bool = False
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps({
            'topic': self.topic,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'qos': self.qos,
            'retain': self.retain
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MQTTMessage':
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls(
            topic=data['topic'],
            payload=data['payload'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            qos=data.get('qos', 0),
            retain=data.get('retain', False)
        )


class AetherMQTTClient:
    """
    MQTT client for AETHER agent communication.
    
    Handles publishing and subscribing to MQTT topics for inter-agent
    messaging with automatic reconnection and message buffering.
    """
    
    def __init__(self, broker: str = None, port: int = None, 
                 username: str = None, password: str = None,
                 topic_prefix: str = "aether"):
        """
        Initialize the MQTT client.
        
        Args:
            broker: MQTT broker address (default from env or localhost)
            port: MQTT broker port (default from env or 1883)
            username: MQTT username (optional)
            password: MQTT password (optional)
            topic_prefix: Prefix for all AETHER topics
        """
        # Load environment variables
        load_dotenv()
        
        # Configuration
        self.broker = broker or os.getenv('MQTT_BROKER', 'localhost')
        self.port = port or int(os.getenv('MQTT_PORT', '1883'))
        self.username = username or os.getenv('MQTT_USERNAME')
        self.password = password or os.getenv('MQTT_PASSWORD')
        self.topic_prefix = topic_prefix
        
        # Create MQTT client
        self.client = mqtt.Client(client_id=f"aether_{datetime.now().timestamp()}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Message handlers
        self.message_handlers: Dict[str, Callable[[MQTTMessage], None]] = {}
        self.message_buffer: list = []
        self.is_connected = False
        
        # Statistics
        self.messages_published = 0
        self.messages_received = 0
        self.connection_errors = 0
    
    def connect(self) -> bool:
        """
        Connect to the MQTT broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Set credentials if provided
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Connect to broker
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, keepalive=60)
            
            # Start network loop
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10  # seconds
            start_time = datetime.now()
            while not self.is_connected and (datetime.now() - start_time).total_seconds() < timeout:
                pass
            
            if self.is_connected:
                logger.info("Successfully connected to MQTT broker")
                return True
            else:
                logger.error("Failed to connect to MQTT broker (timeout)")
                self.connection_errors += 1
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            self.connection_errors += 1
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        logger.info("Disconnecting from MQTT broker")
        self.client.loop_stop()
        self.client.disconnect()
        self.is_connected = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.is_connected = True
            
            # Subscribe to default topics
            self.subscribe("anomaly/alert")
            self.subscribe("orchestrator/status")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")
            self.is_connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects from broker."""
        if rc != 0:
            logger.warning(f"Unexpectedly disconnected from MQTT broker, return code {rc}")
        self.is_connected = False
    
    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received."""
        try:
            # Parse message
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Create message object
            message = MQTTMessage(
                topic=topic,
                payload=payload,
                timestamp=datetime.now(),
                qos=msg.qos,
                retain=msg.retain
            )
            
            # Update statistics
            self.messages_received += 1
            
            # Call handler if registered
            handler = self.message_handlers.get(topic)
            if handler:
                handler(message)
            else:
                # Buffer unhandled messages
                self.message_buffer.append(message)
                logger.debug(f"Buffered message on topic {topic}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def publish(self, topic: str, payload: Dict[str, Any], 
                qos: int = 0, retain: bool = False) -> bool:
        """
        Publish a message to an MQTT topic.
        
        Args:
            topic: Topic to publish to (without prefix)
            payload: Message payload as dictionary
            qos: Quality of Service level (0, 1, or 2)
            retain: Whether to retain message on broker
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.is_connected:
            logger.warning("Not connected to MQTT broker, buffering message")
            self.message_buffer.append(MQTTMessage(
                topic=topic,
                payload=payload,
                timestamp=datetime.now(),
                qos=qos,
                retain=retain
            ))
            return False
        
        try:
            # Add topic prefix
            full_topic = f"{self.topic_prefix}/{topic}"
            
            # Convert payload to JSON
            payload_json = json.dumps(payload)
            
            # Publish message
            result = self.client.publish(full_topic, payload_json, qos=qos, retain=retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.messages_published += 1
                logger.debug(f"Published message to {full_topic}")
                return True
            else:
                logger.error(f"Failed to publish message to {full_topic}, return code {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False
    
    def subscribe(self, topic: str, callback: Optional[Callable[[MQTTMessage], None]] = None) -> bool:
        """
        Subscribe to an MQTT topic.
        
        Args:
            topic: Topic to subscribe to (without prefix)
            callback: Optional callback function for messages on this topic
            
        Returns:
            True if subscribed successfully, False otherwise
        """
        if not self.is_connected:
            logger.warning("Not connected to MQTT broker")
            return False
        
        try:
            # Add topic prefix
            full_topic = f"{self.topic_prefix}/{topic}"
            
            # Subscribe to topic
            result = self.client.subscribe(full_topic)
            
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                # Register callback if provided
                if callback:
                    self.message_handlers[full_topic] = callback
                
                logger.info(f"Subscribed to {full_topic}")
                return True
            else:
                logger.error(f"Failed to subscribe to {full_topic}, return code {result[0]}")
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to topic: {e}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """
        Unsubscribe from an MQTT topic.
        
        Args:
            topic: Topic to unsubscribe from (without prefix)
            
        Returns:
            True if unsubscribed successfully, False otherwise
        """
        if not self.is_connected:
            logger.warning("Not connected to MQTT broker")
            return False
        
        try:
            # Add topic prefix
            full_topic = f"{self.topic_prefix}/{topic}"
            
            # Unsubscribe from topic
            result = self.client.unsubscribe(full_topic)
            
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                # Remove callback if registered
                if full_topic in self.message_handlers:
                    del self.message_handlers[full_topic]
                
                logger.info(f"Unsubscribed from {full_topic}")
                return True
            else:
                logger.error(f"Failed to unsubscribe from {full_topic}, return code {result[0]}")
                return False
                
        except Exception as e:
            logger.error(f"Error unsubscribing from topic: {e}")
            return False
    
    def get_buffered_messages(self) -> list:
        """Get all buffered messages."""
        return self.message_buffer.copy()
    
    def clear_buffer(self) -> None:
        """Clear the message buffer."""
        self.message_buffer.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            'is_connected': self.is_connected,
            'messages_published': self.messages_published,
            'messages_received': self.messages_received,
            'connection_errors': self.connection_errors,
            'buffered_messages': len(self.message_buffer),
            'registered_handlers': len(self.message_handlers)
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Convenience functions for common AETHER topics
def publish_solara_forecast(client: AetherMQTTClient, forecast: Dict[str, Any]) -> bool:
    """Publish a Solara power forecast."""
    return client.publish("solara/forecast", forecast)


def publish_veridian_request(client: AetherMQTTClient, request: Dict[str, Any]) -> bool:
    """Publish a Veridian resource request."""
    return client.publish("veridian/request", request)


def publish_hal_90_decision(client: AetherMQTTClient, decision: Dict[str, Any]) -> bool:
    """Publish a Hal-90 resource allocation decision."""
    return client.publish("hal_90/decision", decision)


def publish_anomaly_alert(client: AetherMQTTClient, anomaly: Dict[str, Any]) -> bool:
    """Publish an anomaly alert."""
    return client.publish("anomaly/alert", anomaly)


def publish_orchestrator_status(client: AetherMQTTClient, status: Dict[str, Any]) -> bool:
    """Publish orchestrator status."""
    return client.publish("orchestrator/status", status)
