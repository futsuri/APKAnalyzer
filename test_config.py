from src.core.config import APKTOOL_PATH, JADX_PATH, JAVA_PATH, TIMEOUT
from pathlib import Path

print("=" * 50)
print("ПРОВЕРКА КОНФИГУРАЦИИ")
print("=" * 50)
print(f"APKTOOL_PATH: {APKTOOL_PATH}")
print(f"JADX_PATH:    {JADX_PATH}")
print(f"JAVA_PATH:    {JAVA_PATH}")
print(f"TIMEOUT:      {TIMEOUT}")
print()
print("ПРОВЕРКА СУЩЕСТВОВАНИЯ ФАЙЛОВ:")
print(f"apktool: {Path(APKTOOL_PATH).exists()}")
print(f"jadx:    {Path(JADX_PATH).exists()}")
print(f"java:    {Path(JAVA_PATH).exists()}")