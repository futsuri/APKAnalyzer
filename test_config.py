from src.core.config import APKTOOL_PATH, JADX_PATH, JAVA_PATH, TIMEOUT
from pathlib import Path
import shutil


def tool_exists(tool_path: str) -> bool:
    candidate = Path(tool_path)
    if candidate.exists():
        return True
    # Если указан alias команды (apktool/jadx/java), проверяем через PATH.
    return shutil.which(tool_path) is not None

print("=" * 50)
print("ПРОВЕРКА КОНФИГУРАЦИИ")
print("=" * 50)
print(f"APKTOOL_PATH: {APKTOOL_PATH}")
print(f"JADX_PATH:    {JADX_PATH}")
print(f"JAVA_PATH:    {JAVA_PATH}")
print(f"TIMEOUT:      {TIMEOUT}")
print()
print("ПРОВЕРКА СУЩЕСТВОВАНИЯ ФАЙЛОВ:")
print(f"apktool: {tool_exists(APKTOOL_PATH)}")
print(f"jadx:    {tool_exists(JADX_PATH)}")
print(f"java:    {tool_exists(JAVA_PATH)}")