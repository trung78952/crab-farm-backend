from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

from app.core.config import settings

logger = logging.getLogger(__name__)


SUBSCRIBE_TOPICS = [
    "farm/motion/ack",
    "farm/motion/status",
    "farm/motion/error",
    "farm/camera/status",
    "farm/camera/result",
]


class MQTTManager:
    def __init__(self) -> None:
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt_client_id,
            reconnect_on_failure=True,
        )
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.connected = False

    def connect(self) -> None:
        try:
            self.client.connect(settings.mqtt_host, settings.mqtt_port, settings.mqtt_keepalive)
            self.client.loop_start()
        except Exception:
            logger.exception("Could not connect to MQTT broker")

    def disconnect(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False

    def publish_json(self, topic: str, payload: dict[str, Any], qos: int = 0) -> None:
        info = self.client.publish(topic, json.dumps(payload, default=str), qos=qos)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed with rc={info.rc}")

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        if reason_code == 0 or str(reason_code).lower() == "success":
            self.connected = True
            for topic in SUBSCRIBE_TOPICS:
                client.subscribe(topic)
            logger.info("Connected to MQTT broker and subscribed to topics")
            return

        self.connected = False
        logger.warning("MQTT connect failed: %s", reason_code)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        self.connected = False
        logger.warning("MQTT disconnected: %s", reason_code)

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        payload_text = message.payload.decode("utf-8", errors="replace")
        from app.services.mqtt_service import handle_incoming_mqtt_message

        try:
            asyncio.run(handle_incoming_mqtt_message(message.topic, payload_text, message.qos))
        except Exception:
            logger.exception("Failed to process MQTT message topic=%s", message.topic)


mqtt_manager = MQTTManager()
