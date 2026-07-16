"""Веб-интерфейс APK Analyzer (FastAPI).

Веб-контейнер оркестрирует остальными сервисами через docker compose:
  - поднять/остановить эмулятор
  - запустить статический/динамический анализ через `docker compose run`

Монтирует /var/run/docker.sock, чтобы дёргать docker CLI из контейнера.
"""

import os
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
app = FastAPI(title="APK Analyzer")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "data" / "output"
STATIC_OUTPUT_DIR = OUTPUT_DIR / "static"
DYNAMIC_OUTPUT_DIR = OUTPUT_DIR / "dynamic"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DYNAMIC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

# Рабочая директория compose-стека. В контейнере это корень проекта
# (туда смонтирован compose-файл через COPY в Dockerfile.web).
PROJECT_DIR = Path(os.getenv("PROJECT_DIR", str(BASE_DIR)))

# Хранилище статусов анализов
analysis_status: dict[str, dict] = {}


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def get_analysis_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _run_compose(args: list[str], timeout: int = 60) -> tuple[int, str]:
    """Запускает `docker compose <args>` в PROJECT_DIR.

    Возвращает (returncode, output). Кодировка — utf-8 с replace, чтобы
    не падать на не-UTF8 байтах в выводе эмулятора/adb.
    """
    cmd = ["docker", "compose", *args]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s"
    except FileNotFoundError:
        return 127, "docker not found"


def _set_status(analysis_id: str, **kwargs):
    """Обновляет поля статуса анализа."""
    if analysis_id not in analysis_status:
        analysis_status[analysis_id] = {"logs": []}
    analysis_status[analysis_id].update(kwargs)


def run_analysis_task(analysis_id: str, apk_name: str, mode: str, package: str | None):
    """Запускает анализ в отдельном потоке через `docker compose run`.

    APK лежит в ./uploads (общий том → /app/input в контейнерах анализа).
    """
    try:
        _set_status(
            analysis_id,
            status="running",
            message="🚀 Запуск анализа...",
            progress=10,
        )
        logs = analysis_status[analysis_id]["logs"]
        logs.append(f"📦 Режим: {mode}")
        if package:
            logs.append(f"📦 Package: {package}")

        # Выбор сервиса по режиму.
        if mode == "static":
            service = "apk-analyzer-static"
        else:
            service = "apk-analyzer-dynamic"

        # APK доступен в контейнере анализа как /app/input/<name> (общий том uploads).
        container_apk = f"/app/input/{apk_name}"
        cmd_args = [
            "run",
            "--rm",
            "--no-deps",
            service,
            container_apk,
            "--mode",
            mode,
        ]
        if package:
            cmd_args.extend(["--package", package])

        logs.append(f"🔧 docker compose {' '.join(cmd_args)}")
        _set_status(analysis_id, progress=30, message="⏳ Анализ выполняется...")

        # Запускаем процесс и стримим вывод построчно.
        full_cmd = ["docker", "compose", *cmd_args]
        process = subprocess.Popen(
            full_cmd,
            cwd=str(PROJECT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        for line in iter(process.stdout.readline, ""):
            if line:
                logs.append(line.rstrip())

        process.wait()

        if process.returncode == 0:
            _set_status(
                analysis_id,
                status="completed",
                message="✅ Анализ завершён!",
                progress=100,
            )
            logs.append("✅ Анализ успешно завершён")

            # Ищем отчёт в соответствующей папке.
            out_dir = STATIC_OUTPUT_DIR if mode == "static" else DYNAMIC_OUTPUT_DIR
            if mode == "full":
                out_dir = STATIC_OUTPUT_DIR
            report_files = sorted(out_dir.glob("*_report.json"))
            if report_files:
                _set_status(analysis_id, report=str(report_files[-1]))
        else:
            _set_status(
                analysis_id,
                status="error",
                message=f"❌ Анализ завершился с ошибкой (код {process.returncode})",
                error=f"exit code {process.returncode}",
            )
            logs.append(f"❌ exit code {process.returncode}")

    except Exception as e:
        _set_status(
            analysis_id,
            status="error",
            message=f"❌ Ошибка: {e}",
            error=str(e),
        )
        analysis_status[analysis_id]["logs"].append(f"❌ {e}")


# ============================================================
# МАРШРУТЫ: UI
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ============================================================
# МАРШРУТЫ: загрузка APK
# ============================================================
@app.post("/api/upload")
async def upload_apk(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return JSONResponse(
            {"success": True, "filename": file.filename, "path": str(file_path)}
        )
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ============================================================
# МАРШРУТЫ: анализ
# ============================================================
@app.post("/api/analyze")
async def start_analysis(
    apk_path: str = Form(...),
    mode: str = Form(...),
    package: str = Form(None),
):
    apk = Path(apk_path)
    if not apk.exists() and not (UPLOAD_DIR / apk.name).exists():
        return JSONResponse(
            {"success": False, "error": f"APK файл не найден: {apk_path}"},
            status_code=400,
        )

    if mode in ("dynamic", "full") and not package:
        return JSONResponse(
            {"success": False, "error": "Package Name обязателен для динамического анализа"},
            status_code=400,
        )

    analysis_id = get_analysis_id()
    analysis_status[analysis_id] = {
        "status": "starting",
        "message": "⏳ Подготовка...",
        "progress": 0,
        "logs": [],
    }

    thread = threading.Thread(
        target=run_analysis_task,
        args=(analysis_id, apk.name, mode, package),
    )
    thread.daemon = True
    thread.start()

    return JSONResponse({"success": True, "analysis_id": analysis_id})


@app.get("/api/status/{analysis_id}")
async def get_status(analysis_id: str):
    if analysis_id not in analysis_status:
        return JSONResponse({"status": "not_found"})

    data = analysis_status[analysis_id]
    return JSONResponse(
        {
            "status": data.get("status", "unknown"),
            "message": data.get("message", ""),
            "progress": data.get("progress", 0),
            "logs": data.get("logs", [])[-100:],
            "report": data.get("report"),
            "error": data.get("error"),
        }
    )


@app.get("/api/report/{analysis_id}")
async def get_report(analysis_id: str):
    if analysis_id not in analysis_status:
        return JSONResponse({"error": "Анализ не найден"}, status_code=404)

    report_path = analysis_status[analysis_id].get("report")
    if not report_path or not Path(report_path).exists():
        return JSONResponse({"error": "Отчёт не найден"}, status_code=404)

    return FileResponse(
        report_path,
        filename=Path(report_path).name,
        media_type="application/json",
    )


# ============================================================
# МАРШРУТЫ: управление Docker-стеком
# ============================================================
@app.get("/api/check-docker")
async def check_docker():
    """Проверяет, что docker-демон отвечает."""
    code, _ = _run_compose(["version"], timeout=10)
    if code == 0:
        return JSONResponse({"running": True, "message": "✅ Docker запущен"})
    return JSONResponse({"running": False, "message": "❌ Docker не отвечает"})


@app.get("/api/docker/emulator/status")
async def emulator_status():
    """Статус сервиса эмулятора: running / exited / absent."""
    code, output = _run_compose(["ps", "android-emulator"], timeout=15)
    if code != 0:
        return JSONResponse(
            {"running": False, "status": "unknown", "message": output[:200]}
        )
    running = "Up" in output and "android-emulator" in output
    state = "running" if running else "stopped"
    return JSONResponse({"running": running, "status": state})


@app.post("/api/docker/emulator/start")
async def emulator_start():
    """Поднимает долгоживущий сервис эмулятора."""
    code, output = _run_compose(["up", "-d", "android-emulator"], timeout=300)
    ok = code == 0
    return JSONResponse(
        {"success": ok, "message": "✅ Эмулятор запускается" if ok else output[:300]}
    )


@app.post("/api/docker/emulator/stop")
async def emulator_stop():
    """Останавливает эмулятор."""
    code, output = _run_compose(["stop", "android-emulator"], timeout=60)
    ok = code == 0
    return JSONResponse(
        {"success": ok, "message": "🛑 Эмулятор остановлен" if ok else output[:300]}
    )
