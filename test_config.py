import shutil
from pathlib import Path
from src.core.config import APKTOOL_PATH, JADX_PATH, JAVA_PATH, TIMEOUT

print("=" * 50)
print("ПРОВЕРКА КОНФИГУРАЦИИ")
print("=" * 50)
print(f"APKTOOL_PATH: {APKTOOL_PATH}")
print(f"JADX_PATH:    {JADX_PATH}")
print(f"JAVA_PATH:    {JAVA_PATH}")
print(f"TIMEOUT:      {TIMEOUT}")
print()


def check_tool(path_str):
    if Path(path_str).exists():
        return True
    if shutil.which(path_str) is not None:
        return True
    return False


print("ПРОВЕРКА СУЩЕСТВОВАНИЯ ФАЙЛОВ:")
print(f"apktool: {check_tool(APKTOOL_PATH)}")
print(f"jadx:    {check_tool(JADX_PATH)}")
print(f"java:    {check_tool(JAVA_PATH)}")