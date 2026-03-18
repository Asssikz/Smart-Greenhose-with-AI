"""
Outer Pico — голосовое управление теплицей.
Запускается через main.py:
    from OuterPico.outer import main_loop
    while True:
        main_loop()
"""

import os
import gc
import time
import socket
import ujson
import bluetooth
from micropython import const

from machine import Pin, I2S, SPI
from OuterPico.sdcard import SDCard
from OuterPico.system_prompt import system_prompt
from pibody import display, Buzzer, LED, Button
from config import I2S_CONFIG, MicroSD_CONFIG, STATE_MACHINE, OUTER_MODULES
from secrets import API_CONFIG, SSID, PASSWORD

try:
    import ssl
except ImportError:
    import ussl as ssl

import urequests


# ── SPI / SD ──────────────────────────────────────────────────────────────────
cs  = Pin(MicroSD_CONFIG['cs'], Pin.OUT)
spi = SPI(
    0,
    baudrate=400000,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=Pin(MicroSD_CONFIG['sck']),
    mosi=Pin(MicroSD_CONFIG['mosi']),
    miso=Pin(MicroSD_CONFIG['miso']),
)
sd = SDCard(spi, cs)
os.mount(sd, "/sd")
print("SD mounted OK")


# ── Helpers ───────────────────────────────────────────────────────────────────

# Display Functions ────────────────────────────────────────────────────────────

def telemetry_status():
    tele = telemetry_data.get("tel")
    display.text("Умная теплица", (240-len("Умная теплица")*8)//2-40, 3, fg=display.WHITE, font=display.font_medium)
    
    next_line = 10+13
    display.text("Температура: " + str(tele["t"]) + " C  ", 10, next_line)
    next_line += 13
    display.linear_bar(10, next_line+8, 160, value=tele["t"], min_value=20, max_value=30, height=8, border=True, color=display.RED)
    next_line += 4
    next_line += 13
    display.text("Влажность: " + str(tele["h"]) + " %  ", 10, next_line)
    next_line += 13
    display.linear_bar(10, next_line+8, 160, value=tele["h"], min_value=0, max_value=100, height=8, border=True, color=display.CYAN)
    next_line += 4
    next_line += 13
    display.text("Освещенность: " + str(tele["l"]), 10, next_line)
    next_line += 13
    display.linear_bar(10, next_line+8, 160, value=tele["l"], min_value=0, max_value=1, height=8, border=True, color=display.YELLOW)
    next_line += 4
    next_line += 13
    display.text("Влажность почвы: " + str(tele["s"]), 10, next_line)
    next_line += 13
    display.linear_bar(10, next_line+8, 160, value=tele["s"], min_value=0, max_value=1, height=8, border=True, color=display.GREEN)
    # 126
    next_line = 126+16
    act = telemetry_data.get("act")
    display.text("Куллер ", 10, next_line, fg=display.GREEN if act["c"] else display.RED)
    display.text("|", 10 + len("Куллер ")*8, next_line, fg=display.WHITE)
    display.text("Отопитель", 10 + len("Куллер ")*8 + len("/ ")*8, next_line, fg=display.GREEN if act["h"] else display.RED)
    next_line += 14
    display.text("Окна ", 10, next_line, fg=display.GREEN if (act["w1"] and act["w2"]) else display.RED)
    display.text("|", 10 + len("Куллер ")*8, next_line, fg=display.WHITE)
    display.text("Дверь ", 10 + len("Куллер ")*8 + len("/ ")*8, next_line, fg=display.GREEN if act["d"] else display.RED)
    next_line += 14
    display.text("Лампа ", 10, next_line, fg=display.GREEN if act["lg"] else display.RED)
    display.text("|", 10 + len("Куллер ")*8, next_line, fg=display.WHITE)
    display.text("Насос ", 10 + len("Куллер ")*8 + len("/ ")*8, next_line, fg=display.GREEN if act["p"] else display.RED)

def stt_status(text):
    display.fill_rect(0, 190, 240, 29, display.BLACK)
    display.hline(0, 190, 240, display.WHITE)
    display.text("Ваш запрос:", 10, 192, fg=display.WHITE)
    text_wrap(text, 10, 192+14, max_lines=2)

def gpt_status(text):
    display.fill_rect(0, 244, 240, 29, display.BLACK)
    display.hline(0, 244, 240, display.WHITE)
    display.text("Ответ:", 10, 246, fg=display.WHITE)
    text_wrap(text, 10, 246+14, max_lines=1)

def debug_status(text):
    display.fill_rect(0, 300, 240, 20, display.WHITE)
    display.text(text, 10, 302, fg=display.BLACK, bg=display.WHITE)

def WiFi_status(arg):
    if arg == 0:
        display.text("Wi-Fi", 240-len("Wi-Fi")*8, 1, fg=display.GREEN)
    elif arg == 1:
        display.text("Wi-Fi", 240-len("Wi-Fi")*8, 1, fg=display.WHITE)
    elif arg == 2:
        display.text("Wi-Fi", 240-len("Wi-Fi")*8, 1, fg=display.RED)

def BLE_status(arg):
    if arg == 0:
        display.text("BLE", 240-len("BLE")*8, 15, fg=display.BLUE)
    elif arg == 1:
        display.text("BLE", 240-len("BLE")*8, 15, fg=display.WHITE)
    elif arg == 2:
        display.text("BLE", 240-len("BLE")*8, 15, fg=display.RED)

def text_wrap(text, x, y, char_width=8, char_height=12, max_lines=None):
    """Draw text with automatic line wrapping. Width 240, font 8×12."""
    max_chars = (240 - x) // char_width
    if max_chars <= 0:
        return
    lines = []
    line  = ""
    for char in text:
        if char == '\n':
            if line:
                lines.append(line)
                line = ""
        elif len(line) >= max_chars:
            lines.append(line)
            line = char
        else:
            line += char
    if line:
        lines.append(line)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last  = lines[-1]
        lines[-1] = (last[:-3] + "...") if len(last) >= 3 else "..."
    for i, ln in enumerate(lines):
        display.text(ln, x, y + i * char_height)


def next_wav_path():
    try:
        existing = os.listdir("/sd/recordings")
    except OSError:
        os.mkdir("/sd/recordings")
        existing = []
    indices = [int(n[4:8]) for n in existing
               if n.startswith("rec_") and n.endswith(".wav") and n[4:8].isdigit()]
    n = max(indices) + 1 if indices else 0
    return "/sd/recordings/rec_{:04d}.wav".format(n)


def create_wav_header(sample_rate, bits, channels, num_samples):
    datasize = num_samples * channels * bits // 8
    o  = b"RIFF"
    o += (datasize + 36).to_bytes(4, "little")
    o += b"WAVE"
    o += b"fmt "
    o += (16).to_bytes(4, "little")
    o += (1).to_bytes(2, "little")
    o += channels.to_bytes(2, "little")
    o += sample_rate.to_bytes(4, "little")
    o += (sample_rate * channels * bits // 8).to_bytes(4, "little")
    o += (channels * bits // 8).to_bytes(2, "little")
    o += bits.to_bytes(2, "little")
    o += b"data"
    o += datasize.to_bytes(4, "little")
    return o


# ── WiFi ──────────────────────────────────────────────────────────────────────

def connect_wifi():
    import network
    wlan = network.WLAN(network.STA_IF)
    WiFi_status(1)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(1)
    if wlan.isconnected():
        print("WiFi OK:", wlan.ifconfig()[0])
        WiFi_status(0)
    else:
        print("WiFi FAILED, status:", wlan.status())
        WiFi_status(2)


# ── BLE Central (подключение к Inner Pico) ────────────────────────────────────
# UUID сервиса и характеристик должны совпадать с inner.py
_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
_CHAR_TX_UUID   = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")  # Notify ← Inner
_CHAR_RX_UUID   = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")  # Write  → Inner

_IRQ_SCAN_RESULT              = const(5)
_IRQ_SCAN_DONE                = const(6)
_IRQ_PERIPHERAL_CONNECT       = const(7)
_IRQ_PERIPHERAL_DISCONNECT    = const(8)
_IRQ_GATTC_SERVICE_RESULT     = const(9)
_IRQ_GATTC_SERVICE_DONE       = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE   = const(12)
_IRQ_GATTC_NOTIFY             = const(18)
_IRQ_GATTC_WRITE_DONE         = const(17)
_ADV_IND        = const(0x00)
_ADV_DIRECT_IND = const(0x01)

# Данные от Inner (tel, act, auto)
# Формат: tel={t,h,l,s,m}, act={c,h,w1,w2,d,p,lg}, auto={c,h,w,d,l,p}
telemetry_data  = {"tel": {}, "act": {}, "auto": {}}
_ble_rx_buffer  = bytearray()


def _decode_adv_name(adv_data):
    """Парсит Complete Local Name (0x09) из advertising data."""
    i = 0
    while i < len(adv_data):
        if i + 2 > len(adv_data):
            break
        length  = adv_data[i]
        ad_type = adv_data[i + 1]
        if length < 1:
            i += 1
            continue
        if ad_type == 0x09:
            end = i + 2 + length - 1
            if end <= len(adv_data):
                return bytes(adv_data[i + 2:end]).decode("utf-8", "ignore")
        i += 1 + length
    return None


def _ble_irq(event, data):
    global _ble_rx_buffer, telemetry_data
    ble = ble_central._ble

    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        if adv_type in (_ADV_IND, _ADV_DIRECT_IND):
            name = _decode_adv_name(adv_data)
            if name and "InnerPico" in name:
                ble_central._addr_type = addr_type
                ble_central._addr      = bytes(addr)
                ble_central._name      = name
                ble.gap_scan(None)

    elif event == _IRQ_SCAN_DONE:
        if ble_central._scan_done_cb:
            ble_central._scan_done_cb()

    elif event == _IRQ_PERIPHERAL_CONNECT:
        conn_handle, addr_type, addr = data
        ble_central._conn_handle     = conn_handle
        ble.gattc_discover_services(conn_handle)

    elif event == _IRQ_PERIPHERAL_DISCONNECT:
        conn_handle, _, _ = data
        if conn_handle == ble_central._conn_handle:
            ble_central._conn_handle = None
            ble_central._tx_handle   = None
            ble_central._rx_handle   = None
            print("[BLE] Disconnected")
            debug_status("BLE disconnected")

    elif event == _IRQ_GATTC_SERVICE_RESULT:
        conn_handle, start_h, end_h, uuid = data
        if conn_handle == ble_central._conn_handle and uuid == _ENV_SENSE_UUID:
            ble_central._start_handle = start_h
            ble_central._end_handle   = end_h

    elif event == _IRQ_GATTC_SERVICE_DONE:
        if ble_central._conn_handle and ble_central._start_handle is not None:
            ble.gattc_discover_characteristics(
                ble_central._conn_handle,
                ble_central._start_handle,
                ble_central._end_handle,
            )

    elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
        conn_handle, def_h, value_h, props, uuid = data
        if conn_handle == ble_central._conn_handle:
            if uuid == _CHAR_TX_UUID:
                ble_central._tx_handle = value_h
            elif uuid == _CHAR_RX_UUID:
                ble_central._rx_handle = value_h

    elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
        if ble_central._tx_handle is not None and ble_central._rx_handle is not None:
            # Подписываемся на Notify (CCCD = tx_handle + 1)
            cccd = ble_central._tx_handle + 1
            try:
                ble.gattc_write(ble_central._conn_handle, cccd, b"\x01\x00", 0)
            except Exception:
                pass
            if ble_central._conn_cb:
                ble_central._conn_cb()

    elif event == _IRQ_GATTC_NOTIFY:
        conn_handle, value_handle, notify_data = data
        if conn_handle == ble_central._conn_handle and value_handle == ble_central._tx_handle:
            chunk = bytes(notify_data)

            # Framing: Inner может слать BEGIN:<len> … END
            if chunk.startswith(b"BEGIN:"):
                _ble_rx_buffer[:] = b""
                return
            if chunk == b"END":
                pass  # буфер готов — попробуем распарсить ниже
            else:
                _ble_rx_buffer.extend(chunk)
                return  # ждём END или пробуем как single-shot

            try:
                msg = ujson.loads(_ble_rx_buffer.decode("utf-8"))
                if "tel" in msg and "act" in msg:
                    telemetry_data["tel"]  = msg.get("tel", {})
                    telemetry_data["act"]  = msg.get("act", {})
                    telemetry_data["auto"] = msg.get("auto", {})
                    telemetry_status()
                _ble_rx_buffer[:] = b""
            except (ValueError, TypeError):
                if len(_ble_rx_buffer) > 512:
                    _ble_rx_buffer[:] = b""


class _BLECentral:
    def __init__(self):
        self._ble          = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(_ble_irq)
        self._addr_type    = None
        self._addr         = None
        self._name         = None
        self._conn_handle  = None
        self._start_handle = None
        self._end_handle   = None
        self._tx_handle    = None
        self._rx_handle    = None
        self._scan_done_cb = None
        self._conn_cb      = None

    def is_connected(self):
        return (self._conn_handle is not None and
                self._tx_handle  is not None and
                self._rx_handle  is not None)

    def scan_and_connect(self, timeout_ms=10000):
        BLE_status(1)
        self._addr_type    = None
        self._addr         = None
        self._scan_done_cb = lambda: None
        self._ble.gap_scan(int(timeout_ms), 30000, 30000)
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while self._addr is None and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            time.sleep_ms(100)
        if self._addr is None:
            print("[BLE] InnerPico not found")
            debug_status("BLE not found")
            return False
        print("[BLE] Found", self._name, "connecting...")
        self._conn_cb = None
        self._ble.gap_connect(self._addr_type, self._addr)
        deadline = time.ticks_add(time.ticks_ms(), 5000)
        while not self.is_connected() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            time.sleep_ms(50)
        if self.is_connected():
            print("[BLE] Connected to InnerPico")
            BLE_status(0)
        return self.is_connected()

    def write(self, data):
        """Отправка команды на Inner (RX char).
        Если команд несколько (через ;), отправляет каждую отдельным пакетом.
        """
        if not self.is_connected():
            return False
        if isinstance(data, str):
            commands = [c.strip() for c in data.split(";") if c.strip()]
        else:
            commands = [data.decode("utf-8").strip()]

        success = True
        for cmd in commands:
            raw = cmd.encode("utf-8")
            if len(raw) > 20:
                print("[BLE] Command too long ({} bytes), skipping: {}".format(len(raw), cmd))
                success = False
                continue
            try:
                self._ble.gattc_write(self._conn_handle, self._rx_handle, raw, 0)
                time.sleep_ms(50)  # небольшая пауза между командами
            except Exception as e:
                print("[BLE] Write error:", e)
                success = False
        return success


print("Initializing BLE central...")
ble_central = _BLECentral()
print("BLE central initialized")


# ── STT ───────────────────────────────────────────────────────────────────────

def stream_transcribe(file_path, api_key):
    host     = "mangisoz.nu.edu.kz"
    path     = "/backend/api/v1/stt/transcribe"
    boundary = "PicoWStreamBoundary"

    file_size = os.stat(file_path)[6]

    def field(name, value):
        return "--{}\r\nContent-Disposition: form-data; name=\"{}\"\r\n\r\n{}\r\n".format(
            boundary, name, value)

    fields = [
        field("language",        "auto"),
        field("response_format", "json"),
        field("temperature",     "1"),
        field("include_raw",     "false"),
        field("stream",          "false"),
    ]

    file_header = "--{}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"{}\"\r\nContent-Type: audio/wav\r\n\r\n".format(
        boundary, file_path.split("/")[-1])
    file_footer = "\r\n--{}--\r\n".format(boundary)

    content_length = sum(len(f) for f in fields) + len(file_header) + file_size + len(file_footer)

    addr  = socket.getaddrinfo(host, 443)[0][-1]
    raw_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_s.connect(addr)
    s = ssl.wrap_socket(raw_s, server_hostname=host)

    headers = (
        "POST {} HTTP/1.1\r\n"
        "Host: {}\r\n"
        "X-API-Key: {}\r\n"
        "Content-Type: multipart/form-data; boundary={}\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n\r\n"
    ).format(path, host, api_key, boundary, content_length)

    s.write(headers.encode())
    for f in fields:
        s.write(f.encode())
    s.write(file_header.encode())

    with open(file_path, "rb") as f:
        buf = bytearray(512)
        while True:
            n = f.readinto(buf)
            if n == 0:
                break
            s.write(buf[:n])

    s.write(file_footer.encode())

    while True:
        line = s.readline()
        if not line or line == b"\r\n":
            break

    body = bytearray()
    while True:
        chunk = s.read(256)
        if not chunk:
            break
        body.extend(chunk)
    s.close()
    return ujson.loads(body.decode())["text"]


# ── GPT ───────────────────────────────────────────────────────────────────────

def ask_gpt(prompt_text, openai_key):
    url     = API_CONFIG['LLM_URL']
    headers = {
        "Content-Type":  "application/json",
        "Authorization": "Bearer " + openai_key,
    }
    payload = {
        "model": API_CONFIG['MODEL'],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt_text},
        ],
    }
    try:
        res    = urequests.post(url, data=ujson.dumps(payload).encode("utf-8"), headers=headers)
        result = res.json()
        res.close()
        if "choices" in result:
            return result["choices"][0]["message"]["content"].strip().replace("`", "")
        return "print('No choices')"
    except Exception as e:
        print("LLM error:", e)
        return "print('LLM Error')"


# ── Pipeline: запись → STT → GPT → отправка на Inner ─────────────────────────

def process_recording(filepath):
    global audio_in

    print("Processing:", filepath)
    debug_status("Processing...")

    # ── Отключаем BLE перед WiFi: CYW43 не тянет оба одновременно ────────────
    print("[BLE] Suspending for WiFi...")
    BLE_status(2)
    try:
        ble_central._conn_handle  = None
        ble_central._tx_handle    = None
        ble_central._rx_handle    = None
        ble_central._ble.active(False)
    except Exception as e:
        print("[BLE] Deactivate error:", e)
    time.sleep_ms(300)

    connect_wifi()
    gc.collect()

    text = None
    try:
        print("Transcribing...")
        debug_status("Transcribing...")
        text = stream_transcribe(filepath, API_CONFIG['STT_KEY'])
        stt_status(text)
        print("Text:", text)
    except Exception as e:
        print("STT error:", e)

    code = None
    if text:
        try:
            print("Asking LLM...")
            debug_status("Asking AlemLLM...")
            code = ask_gpt(text, API_CONFIG['LLM_KEY'])
            gpt_status(code)
            print("Code:", code)
        except Exception as e:
            print("LLM error:", e)

    # ── Отключаем WiFi, восстанавливаем BLE ──────────────────────────────────
    print("[WiFi] Disconnecting...")
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        wlan.disconnect()
        wlan.active(False)
        WiFi_status(2)  
    except Exception as e:
        print("[WiFi] Disconnect error:", e)
    time.sleep_ms(300)

    print("[BLE] Restoring...")
    debug_status("BLE restoring...")
    BLE_status(1)
    try:
        ble_central._ble.active(True)
        ble_central._ble.irq(_ble_irq)
        BLE_status(0)
    except Exception as e:
        print("[BLE] Reactivate error:", e)
    time.sleep_ms(300)

    if not ble_central.is_connected():
        print("[BLE] Reconnecting to Greenhouse...")
        debug_status("Reconnecting to Greenhouse...")
        BLE_status(1)
        ble_central.scan_and_connect(timeout_ms=8000)

    if code:
        if ble_central.write(code):
            print("Sent to Inner:", code)
            debug_status("Sent to Greenhouse")
        else:
            print("[BLE] Not connected, cannot send")
            debug_status("BLE not connected, can't send")

    gc.collect()
    reinit_microphone()


# ── Globals shared with I2S callback ─────────────────────────────────────────
state                           = STATE_MACHINE['PAUSE']
num_sample_bytes_written_to_wav = 0
num_read                        = 0
# mic_samples — половина ibuf: IRQ срабатывает когда половина буфера заполнена,
# за это время пишем предыдущую половину. Так снижается нагрузка на CPU.
_MIC_BUF_SIZE = I2S_CONFIG['ibuf'] // 2
mic_samples   = bytearray(_MIC_BUF_SIZE)
mic_samples_mv                  = memoryview(mic_samples)
wav                             = None
last_filepath                   = None
recording_done                  = False


def i2s_callback_rx(arg):
    global state, num_sample_bytes_written_to_wav, num_read, wav
    global recording_done

    if state == STATE_MACHINE['RECORD']:
        wav.write(mic_samples_mv[:num_read])
        num_sample_bytes_written_to_wav += num_read
        num_read = audio_in.readinto(mic_samples_mv)

    elif state == STATE_MACHINE['RESUME']:
        state    = STATE_MACHINE['RECORD']
        num_read = audio_in.readinto(mic_samples_mv)

    elif state == STATE_MACHINE['PAUSE']:
        num_read = audio_in.readinto(mic_samples_mv)

    elif state == STATE_MACHINE['STOP']:
        # Переключаем сразу, чтобы не войти сюда повторно
        state = STATE_MACHINE['PAUSE']
        header = create_wav_header(
            I2S_CONFIG['rate'],
            I2S_CONFIG['bits'],
            I2S_CONFIG['nch'],
            num_sample_bytes_written_to_wav // (I2S_CONFIG['bits'] // 8 * I2S_CONFIG['nch']),
        )
        wav.seek(0)
        wav.write(header)
        wav.close()
        print("WAV saved.")
        recording_done = True
        # Продолжаем читать, чтобы IRQ-цепочка не оборвалась
        num_read = audio_in.readinto(mic_samples_mv)


# ── I2S init ──────────────────────────────────────────────────────────────────

def init_i2s():
    # ibuf должен быть 4096 в config.py (не WAV_SAMPLE_SIZE_IN_BYTES!)
    _audio = I2S(
        I2S_CONFIG['id'],
        sck    = Pin(I2S_CONFIG['sck']),
        ws     = Pin(I2S_CONFIG['ws']),
        sd     = Pin(I2S_CONFIG['sd']),
        mode   = I2S.RX,
        bits   = I2S_CONFIG['bits'],
        format = I2S.MONO,
        rate   = I2S_CONFIG['rate'],
        ibuf   = I2S_CONFIG['ibuf'],
    )
    _audio.irq(i2s_callback_rx)
    return _audio


def reinit_microphone():
    """Deinit existing I2S and create a fresh one."""
    global audio_in
    try:
        audio_in.deinit()
    except Exception:
        pass
    audio_in = init_i2s()
    print("Mic reinit OK")


audio_in = init_i2s()

# ── Hardware ──────────────────────────────────────────────────────────────────
button = Button(OUTER_MODULES['BUTTON'])
buzzer = Buzzer(OUTER_MODULES['BUZZER'])
led    = LED(OUTER_MODULES['LED'])

debounce_ms    = 50
last_btn_state = button.value()
last_change_ms = time.ticks_ms()
recording      = False

connect_wifi()
ble_central.scan_and_connect()
print("Ready. Press button to start/stop recording.")
debug_status("Press button to start")


# ── main_loop — вызывается из main.py ─────────────────────────────────────────

def main_loop():
    global state, wav, last_filepath, num_sample_bytes_written_to_wav
    global num_read, recording_done, recording, last_btn_state, last_change_ms

    # Если запись только что завершилась — обрабатываем
    if recording_done:
        recording_done = False
        process_recording(last_filepath)

    # Кнопка с дебаунсом
    now       = time.ticks_ms()
    btn_state = button.value()

    if btn_state != last_btn_state and time.ticks_diff(now, last_change_ms) > debounce_ms:
        last_btn_state = btn_state
        last_change_ms = now

        if btn_state == 1:          # кнопка нажата
            if not recording:
                last_filepath                   = next_wav_path()
                wav                             = open(last_filepath, "wb")
                wav.seek(44)
                num_sample_bytes_written_to_wav = 0
                recording                       = True
                state                           = STATE_MACHINE['RECORD']
                num_read                        = audio_in.readinto(mic_samples_mv)
                print("● REC →", last_filepath)
                debug_status("Recording...")
            else:
                recording = False
                state     = STATE_MACHINE['STOP']
                debug_status("Stopping...")
                print("■ Stopping...")

    time.sleep_ms(10)