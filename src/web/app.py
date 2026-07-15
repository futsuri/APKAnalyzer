import os
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime

# ============================================================
# НАСТРОЙКА
# ============================================================
app = FastAPI(title="APK Analyzer")
BASE_DIR = Path(__file__).parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "data" / "output" / "static"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

# Хранилище статусов анализов
analysis_status = {}

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def get_analysis_id():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_analysis_task(analysis_id: str, apk_path: str, mode: str, package: str = None):
    """Запускает анализ в отдельном потоке"""
    try:
        analysis_status[analysis_id] = {
            "status": "running",
            "message": "🚀 Запуск анализа...",
            "progress": 10,
            "logs": []
        }
        
        # Определяем скрипт в зависимости от ОС
        if os.name == 'nt':  # Windows
            script_path = str(BASE_DIR / "run_analyzer.bat")
        else:  # Linux/macOS
            script_path = str(BASE_DIR / "run_analyzer.sh")
        
        # Строим команду
        cmd = [script_path, apk_path, "--mode", mode]
        if package:
            cmd.extend(["--package", package])
        
        analysis_status[analysis_id]["logs"].append(f"📂 Скрипт: {script_path}")
        analysis_status[analysis_id]["logs"].append(f"📦 Режим: {mode}")
        if package:
            analysis_status[analysis_id]["logs"].append(f"📦 Package: {package}")
        
        # Запускаем процесс
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(BASE_DIR),
            shell=True
        )
        
        # Читаем вывод построчно
        for line in iter(process.stdout.readline, ''):
            if line:
                analysis_status[analysis_id]["logs"].append(line.strip())
                if "ERROR" in line or "error" in line.lower():
                    analysis_status[analysis_id]["logs"].append("⚠️ Обнаружена ошибка")
        
        process.wait()
        
        if process.returncode == 0:
            analysis_status[analysis_id]["status"] = "completed"
            analysis_status[analysis_id]["message"] = "✅ Анализ завершён!"
            analysis_status[analysis_id]["progress"] = 100
            analysis_status[analysis_id]["logs"].append("✅ Анализ успешно завершён")
            
            # Находим отчёт
            report_files = list(OUTPUT_DIR.glob("*_report.json"))
            if report_files:
                analysis_status[analysis_id]["report"] = str(report_files[-1])
        else:
            analysis_status[analysis_id]["status"] = "error"
            analysis_status[analysis_id]["message"] = f"❌ Анализ завершился с ошибкой (код {process.returncode})"
            
    except Exception as e:
        analysis_status[analysis_id]["status"] = "error"
        analysis_status[analysis_id]["message"] = f"❌ Ошибка: {str(e)}"
        analysis_status[analysis_id]["logs"].append(f"❌ {str(e)}")


# ============================================================
# МАРШРУТЫ
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/upload")
async def upload_apk(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "path": str(file_path)
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/analyze")
async def start_analysis(
    apk_path: str = Form(...),
    mode: str = Form(...),
    package: str = Form(None)
):
    try:
        if not os.path.exists(apk_path):
            return JSONResponse({
                "success": False,
                "error": f"APK файл не найден: {apk_path}"
            }, status_code=400)
        
        if mode in ["dynamic", "full"] and not package:
            return JSONResponse({
                "success": False,
                "error": "Package Name обязателен для динамического анализа"
            }, status_code=400)
        
        analysis_id = get_analysis_id()
        analysis_status[analysis_id] = {
            "status": "starting",
            "message": "⏳ Подготовка...",
            "progress": 0,
            "logs": []
        }
        
        thread = threading.Thread(
            target=run_analysis_task,
            args=(analysis_id, apk_path, mode, package)
        )
        thread.daemon = True
        thread.start()
        
        return JSONResponse({"success": True, "analysis_id": analysis_id})
        
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/status/{analysis_id}")
async def get_status(analysis_id: str):
    if analysis_id not in analysis_status:
        return JSONResponse({"status": "not_found"})
    
    data = analysis_status[analysis_id]
    return JSONResponse({
        "status": data.get("status", "unknown"),
        "message": data.get("message", ""),
        "progress": data.get("progress", 0),
        "logs": data.get("logs", [])[-50:],
        "report": data.get("report", None),
        "error": data.get("error", None)
    })


@app.get("/api/report/{analysis_id}")
async def get_report(analysis_id: str):
    if analysis_id not in analysis_status:
        return JSONResponse({"error": "Анализ не найден"}, status_code=404)
    
    report_path = analysis_status[analysis_id].get("report")
    if not report_path or not os.path.exists(report_path):
        return JSONResponse({"error": "Отчёт не найден"}, status_code=404)
    
    return FileResponse(
        report_path,
        filename=Path(report_path).name,
        media_type="application/json"
    )


@app.get("/api/check-docker")
async def check_docker():
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return JSONResponse({"running": True, "message": "✅ Docker запущен"})
        else:
            return JSONResponse({"running": False, "message": "❌ Docker не отвечает"})
    except FileNotFoundError:
        return JSONResponse({"running": False, "message": "❌ Docker не установлен"})
    except Exception:
        return JSONResponse({"running": False, "message": "❌ Ошибка проверки Docker"})