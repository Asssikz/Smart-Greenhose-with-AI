import bluetooth
import ujson
import time
import struct
from micropython import const

from InnerPico.telemetry import telemetry_data
from InnerPico.actuators import (
    actuator_state, automation_state,
    cooler_on, cooler_off,
    heater_on, heater_off,
    pump_on, pump_off,
    window_1_open, window_1_close,
    window_2_open, window_2_close,
    door_open, door_close,
    light_on, light_off, light_uv,
    all_windows_open, all_windows_close,
    automation_on, automation_off,
)

# ─────────────────────────────────────────────────────────────
# BLE constants
# ─────────────────────────────────────────────────────────────
_IRQ_CENTRAL_CONNECT    = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE        = const(3)
_IRQ_MTU_EXCHANGED      = const(21)

_FLAG_READ   = const(0x0002)
_FLAG_WRITE  = const(0x0004)
_FLAG_NOTIFY = const(0x0010)

# Стандартный сервис оставим, как у тебя
_ENV_SENSE_UUID = bluetooth.UUID(0x181A)

# Лучше для кастомного обмена использовать vendor-specific UUID
_TX_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
_RX_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

# GATT
ble = bluetooth.BLE()
ble.active(True)

_tx = (_TX_UUID, _FLAG_READ | _FLAG_NOTIFY)
_rx = (_RX_UUID, _FLAG_WRITE)

_service = (_ENV_SENSE_UUID, (_tx, _rx))
((tx_handle, rx_handle),) = ble.gatts_register_services((_service,))

# Увеличиваем буфер на запись
ble.gatts_set_buffer(rx_handle, 512, True)

_conn_handle = None
_att_payload_max = 20   # по умолчанию до MTU exchange


# ─────────────────────────────────────────────────────────────
# Advertising payload
# ─────────────────────────────────────────────────────────────
def advertising_payload(name=None, services=None):
    payload = bytearray()

    def _append(adv_type, value):
        payload.extend(struct.pack("BB", len(value) + 1, adv_type))
        payload.extend(value)

    # Flags: LE General Discoverable + BR/EDR not supported
    _append(0x01, b"\x06")

    if name:
        _append(0x09, name)

    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(0x03, b)   # Complete List of 16-bit Service UUIDs
            elif len(b) == 16:
                _append(0x07, b)   # Complete List of 128-bit Service UUIDs

    return payload


def _advertise(interval_us=250000):
    name = b"InnerPico"
    payload = advertising_payload(name=name, services=[_ENV_SENSE_UUID])
    ble.gap_advertise(interval_us, adv_data=payload)
    print("[BLE] Advertising as 'InnerPico'")


# ─────────────────────────────────────────────────────────────
# Command dispatch instead of exec
# ─────────────────────────────────────────────────────────────
COMMANDS = {
    "cooler_on()": cooler_on,
    "cooler_off()": cooler_off,
    "heater_on()": heater_on,
    "heater_off()": heater_off,
    "pump_on()": pump_on,
    "pump_off()": pump_off,
    "window_1_open()": window_1_open,
    "window_1_close()": window_1_close,
    "window_2_open()": window_2_open,
    "window_2_close()": window_2_close,
    "door_open()": door_open,
    "door_close()": door_close,
    "light_on()": light_on,
    "light_off()": light_off,
    "light_uv()": light_uv,
    "all_windows_open()": all_windows_open,
    "all_windows_close()": all_windows_close,
    "automation_on()": automation_on,
    "automation_off()": automation_off,
}


def _handle_command(raw):
    try:
        cmd = raw.decode("utf-8").strip()
        if not cmd:
            print("[CMD] Empty command")
            return

        print("[CMD] Received:", cmd)

        fn = COMMANDS.get(cmd)
        if fn is None:
            print("[CMD] Unknown command:", cmd)
            return

        fn()
        print("[CMD] Done. State:", actuator_state)

    except Exception as e:
        print("[CMD] Error:", e)


# ─────────────────────────────────────────────────────────────
# IRQ handler
# ─────────────────────────────────────────────────────────────
def _ble_irq(event, data):
    global _conn_handle, _att_payload_max

    if event == _IRQ_CENTRAL_CONNECT:
        conn_handle, _, _ = data
        _conn_handle = conn_handle
        print("[BLE] Central connected:", conn_handle)

    elif event == _IRQ_CENTRAL_DISCONNECT:
        conn_handle, _, _ = data
        if _conn_handle == conn_handle:
            _conn_handle = None
        print("[BLE] Central disconnected:", conn_handle)
        _advertise()

    elif event == _IRQ_MTU_EXCHANGED:
        conn_handle, mtu = data
        if _conn_handle == conn_handle:
            _att_payload_max = max(20, mtu - 3)
        print("[BLE] MTU exchanged:", mtu, "payload:", _att_payload_max)

    elif event == _IRQ_GATTS_WRITE:
        conn_handle, value_handle = data
        if conn_handle == _conn_handle and value_handle == rx_handle:
            raw = ble.gatts_read(rx_handle)
            _handle_command(raw)


ble.irq(_ble_irq)
_advertise()


# ─────────────────────────────────────────────────────────────
# Payload builder
# ─────────────────────────────────────────────────────────────
def _b(v):
    return 1 if v else 0


def _build_payload():
    payload = {
        "tel": {
            "t": telemetry_data.get("temp"),
            "h": telemetry_data.get("humidity"),
            "l": telemetry_data.get("light"),
            "s": telemetry_data.get("soil_moisture"),
            "m": telemetry_data.get("motion"),
        },
        "act": {
            "c":  _b(actuator_state.get("COOLER")),
            "h":  _b(actuator_state.get("HEATER")),
            "w1": _b(actuator_state.get("WINDOW_1")),
            "w2": _b(actuator_state.get("WINDOW_2")),
            "d":  _b(actuator_state.get("DOOR")),
            "p":  _b(actuator_state.get("PUMP")),
            "lg": _b(actuator_state.get("LIGHT")),
        },
        "auto": {
            "c": _b(automation_state.get("COOLER")),
            "h": _b(automation_state.get("HEATER")),
            "w": _b(automation_state.get("WINDOWS")),
            "d": _b(automation_state.get("DOOR")),
            "l": _b(automation_state.get("LIGHT")),
            "p": _b(automation_state.get("PUMP")),
        }
    }
    return ujson.dumps(payload).encode("utf-8")


# ─────────────────────────────────────────────────────────────
# Notify sender with simple framing
# ─────────────────────────────────────────────────────────────
def _notify_one(data):
    if _conn_handle is None:
        return False
    try:
        ble.gatts_notify(_conn_handle, tx_handle, data)
        return True
    except Exception as e:
        print("[TX] Notify error:", e)
        return False


def _notify_telemetry():
    if _conn_handle is None:
        return

    data = _build_payload()
    total_len = len(data)
    chunk_size = _att_payload_max

    print("[TX] Sending {} bytes".format(total_len))

    if total_len <= chunk_size:
        _notify_one(data)
        return

    # Фрейминг для сборки на central
    if not _notify_one(("BEGIN:%d" % total_len).encode("utf-8")):
        return
    time.sleep_ms(10)

    offset = 0
    while offset < total_len:
        chunk = data[offset:offset + chunk_size]
        if not _notify_one(chunk):
            return
        offset += chunk_size
        time.sleep_ms(10)

    _notify_one(b"END")


# ─────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────
_NOTIFY_INTERVAL_MS = const(1000)

def main_loop():
    _notify_telemetry()
    time.sleep_ms(_NOTIFY_INTERVAL_MS)