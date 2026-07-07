# APKAnalyzer

CLI utility for static APK analysis. The Docker image contains all runtime dependencies:

- Python dependencies installed with Poetry
- Java runtime
- apktool
- jadx

## Run with Docker

Build the image:

```bat
scripts\docker-build.bat
```

Analyze an APK:

```bat
scripts\docker-run.bat C:\path\to\app.apk
```

Reports are written to:

```text
data/output/static/
```

You can pass analyzer options after the APK path:

```bat
scripts\docker-run.bat C:\path\to\app.apk --debug
scripts\docker-run.bat C:\path\to\app.apk --output data/output/static
```

## Run with docker compose

Show the CLI help:

```bash
docker compose run --rm apk-analyzer
```

Run analysis by mounting a folder with APK files:

```bash
docker compose run --rm -v "%CD%\data\input\apks:/input:ro" apk-analyzer /input/app.apk
```

## Local run without Docker

Local runs are optional. Install Java, apktool and jadx, then install Python dependencies:

```bash
pip install -r requirements.txt
python main.py path/to/app.apk
```

For local runs you can configure tool paths in `.env`:

```env
APKTOOL_PATH=C:/tools/apktool.bat
JADX_PATH=C:/tools/jadx/bin/jadx.bat
JAVA_PATH=C:/Program Files/Java/bin/java.exe
```

## Configuration check

Inside the Docker image:

```bash
docker run --rm --entrypoint poetry apk-analyzer run python test_config.py
```

On the host:

```bash
python test_config.py
```
