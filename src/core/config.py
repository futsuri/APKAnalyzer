import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).parent.parent.parent  # Корень проекта

DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input" / "apks"
OUTPUT_DIR = DATA_DIR / "output"
STATIC_OUTPUT_DIR = OUTPUT_DIR / "static"
DYNAMIC_OUTPUT_DIR = OUTPUT_DIR / "dynamic"
TEMP_DIR = DATA_DIR / "temp"

for dir_path in [INPUT_DIR, STATIC_OUTPUT_DIR, DYNAMIC_OUTPUT_DIR, TEMP_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Загружаем config.yaml
CONFIG_FILE = BASE_DIR / "config.yaml"

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

_config = load_config()

APKTOOL_PATH = os.getenv('APKTOOL_PATH') or _config.get('tools', {}).get('apktool', 'apktool')
JADX_PATH = os.getenv('JADX_PATH') or _config.get('tools', {}).get('jadx', 'jadx')
JAVA_PATH = os.getenv('JAVA_PATH') or _config.get('tools', {}).get('java', 'java')

TIMEOUT = _config.get('analysis', {}).get('timeout', 600)
MAX_LIBRARIES = _config.get('analysis', {}).get('max_libraries', 50)

DANGEROUS_PERMISSIONS = {
    "READ_PHONE_STATE": "Чтение состояния телефона (IMEI, номер и т.д.)",
    "READ_CONTACTS": "Чтение контактов",
    "ACCESS_FINE_LOCATION": "Точная геолокация",
    "ACCESS_COARSE_LOCATION": "Примерная геолокация",
    "CAMERA": "Доступ к камере",
    "RECORD_AUDIO": "Запись звука",
    "READ_SMS": "Чтение SMS",
    "READ_EXTERNAL_STORAGE": "Чтение внешнего хранилища",
    "WRITE_EXTERNAL_STORAGE": "Запись во внешнее хранилище",
    "READ_CALL_LOG": "Чтение журнала звонков",
    "WRITE_CALL_LOG": "Запись в журнал звонков",
    "SYSTEM_ALERT_WINDOW": "Окна поверх других приложений",
    "POST_NOTIFICATIONS": "Отправка уведомлений",
    "ACCESS_BACKGROUND_LOCATION": "Фоновая геолокация",
    "READ_PHONE_NUMBERS": "Чтение номеров телефона",
    "ANSWER_PHONE_CALLS": "Отвечать на звонки",
}

IDENTIFIER_PATTERNS = {
    "IMEI": ["getDeviceId", "getImei", "getMeid"],
    "Android ID": ["ANDROID_ID", "Settings.Secure"],
    "MAC Address": ["getMacAddress", "WifiInfo", "getHardwareAddress"],
    "Advertising ID": ["AdvertisingIdClient", "getAdvertisingIdInfo"],
    "IMSI": ["getSubscriberId", "getSimSerialNumber"],
    "Serial": ["Build.SERIAL", "getSerial"],
    "Phone Number": ["getLine1Number"],
    "Network Operator": ["getNetworkOperator", "getSimOperator"]
}

if os.getenv('DEBUG'):
    print(f"[CONFIG] APKTOOL_PATH: {APKTOOL_PATH}")
    print(f"[CONFIG] JADX_PATH: {JADX_PATH}")
    print(f"[CONFIG] JAVA_PATH: {JAVA_PATH}")
    print(f"[CONFIG] TIMEOUT: {TIMEOUT}")