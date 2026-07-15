// ============================================================
// СОСТОЯНИЕ
// ============================================================
const state = {
    apkPath: null,
    analysisId: null,
    isRunning: false,
    checkInterval: null
};

// ============================================================
// DOM ЭЛЕМЕНТЫ
// ============================================================
const elements = {
    dropZone: document.getElementById('dropZone'),
    fileInput: document.getElementById('fileInput'),
    selectFileBtn: document.getElementById('selectFileBtn'),
    fileInfo: document.getElementById('fileInfo'),
    fileName: document.getElementById('fileName'),
    fileSize: document.getElementById('fileSize'),
    runBtn: document.getElementById('runBtn'),
    progressSection: document.getElementById('progressSection'),
    progressFill: document.getElementById('progressFill'),
    statusMessage: document.getElementById('statusMessage'),
    logContainer: document.getElementById('logContainer'),
    resultSection: document.getElementById('resultSection'),
    openReportBtn: document.getElementById('openReportBtn'),
    downloadReportBtn: document.getElementById('downloadReportBtn'),
    clearLogsBtn: document.getElementById('clearLogsBtn'),
    packageGroup: document.getElementById('packageGroup'),
    packageInput: document.getElementById('packageInput'),
    dockerStatus: document.getElementById('dockerStatus')
};

// ============================================================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// ============================================================
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function getSelectedMode() {
    const radio = document.querySelector('input[name="mode"]:checked');
    return radio ? radio.value : 'static';
}

function addLog(message, type = 'info') {
    const line = document.createElement('div');
    const time = new Date().toLocaleTimeString();
    line.textContent = `[${time}] ${message}`;
    line.className = `log-${type}`;
    elements.logContainer.appendChild(line);
    elements.logContainer.scrollTop = elements.logContainer.scrollHeight;
}

function clearLogs() {
    elements.logContainer.innerHTML = '';
}

function updateProgress(progress, message) {
    elements.progressFill.style.width = `${progress}%`;
    elements.statusMessage.textContent = message;
}

// ============================================================
// ПРОВЕРКА DOCKER
// ============================================================
async function checkDocker() {
    try {
        const response = await fetch('/api/check-docker');
        const data = await response.json();
        elements.dockerStatus.textContent = data.running ? '✅ ' + data.message : '❌ ' + data.message;
        elements.dockerStatus.style.color = data.running ? '#68d391' : '#fc8181';
        return data.running;
    } catch (error) {
        elements.dockerStatus.textContent = '❌ Ошибка проверки Docker';
        return false;
    }
}

// ============================================================
// ЗАГРУЗКА ФАЙЛА
// ============================================================
elements.selectFileBtn.addEventListener('click', () => {
    elements.fileInput.click();
});

elements.fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// Drag and Drop
elements.dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    elements.dropZone.classList.add('dragover');
});

elements.dropZone.addEventListener('dragleave', () => {
    elements.dropZone.classList.remove('dragover');
});

elements.dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    elements.dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        handleFile(e.dataTransfer.files[0]);
    }
});

async function handleFile(file) {
    if (!file.name.endsWith('.apk')) {
        alert('Пожалуйста, выберите APK файл');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    addLog(`📤 Загрузка: ${file.name} (${formatFileSize(file.size)})`);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (data.success) {
            state.apkPath = data.path;
            elements.fileInfo.style.display = 'flex';
            elements.fileName.textContent = file.name;
            elements.fileSize.textContent = formatFileSize(file.size);
            addLog('✅ Файл загружен', 'success');
            elements.runBtn.disabled = false;
        } else {
            addLog('❌ ' + data.error, 'error');
        }
    } catch (error) {
        addLog('❌ Ошибка загрузки: ' + error.message, 'error');
    }
}

// ============================================================
// РЕЖИМ АНАЛИЗА
// ============================================================
document.querySelectorAll('input[name="mode"]').forEach(radio => {
    radio.addEventListener('change', () => {
        const mode = getSelectedMode();
        elements.packageGroup.style.display = (mode === 'dynamic' || mode === 'full') ? 'block' : 'none';
    });
});

// ============================================================
// ЗАПУСК АНАЛИЗА
// ============================================================
elements.runBtn.addEventListener('click', startAnalysis);

async function startAnalysis() {
    if (!state.apkPath) {
        alert('Сначала загрузите APK файл');
        return;
    }
    
    const mode = getSelectedMode();
    const packageName = elements.packageInput.value.trim();
    
    if ((mode === 'dynamic' || mode === 'full') && !packageName) {
        alert('Укажите Package Name для динамического анализа');
        elements.packageInput.focus();
        return;
    }
    
    if (state.isRunning) return;
    
    state.isRunning = true;
    elements.runBtn.disabled = true;
    elements.runBtn.textContent = '⏳ Анализ выполняется...';
    
    elements.progressSection.style.display = 'block';
    elements.resultSection.style.display = 'none';
    clearLogs();
    updateProgress(0, '⏳ Подготовка...');
    
    const formData = new FormData();
    formData.append('apk_path', state.apkPath);
    formData.append('mode', mode);
    if (packageName) formData.append('package', packageName);
    
    addLog(`🚀 Запуск анализа (режим: ${mode})`);
    if (packageName) addLog(`📦 Package: ${packageName}`);
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (data.success) {
            state.analysisId = data.analysis_id;
            addLog(`✅ Анализ запущен (ID: ${data.analysis_id})`, 'success');
            startPolling(data.analysis_id);
        } else {
            addLog('❌ ' + data.error, 'error');
            state.isRunning = false;
            elements.runBtn.disabled = false;
            elements.runBtn.textContent = '🚀 Запустить анализ';
        }
    } catch (error) {
        addLog('❌ Ошибка: ' + error.message, 'error');
        state.isRunning = false;
        elements.runBtn.disabled = false;
        elements.runBtn.textContent = '🚀 Запустить анализ';
    }
}

// ============================================================
// ОПРОС СТАТУСА
// ============================================================
function startPolling(analysisId) {
    if (state.checkInterval) {
        clearInterval(state.checkInterval);
    }
    
    state.checkInterval = setInterval(() => {
        fetchStatus(analysisId);
    }, 2000);
}

async function fetchStatus(analysisId) {
    try {
        const response = await fetch(`/api/status/${analysisId}`);
        const data = await response.json();
        
        if (data.status === 'not_found') {
            clearInterval(state.checkInterval);
            addLog('⚠️ Анализ не найден', 'warning');
            finishAnalysis();
            return;
        }
        
        updateProgress(data.progress || 0, data.message || '');
        
        // Обновляем логи (показываем только новые)
        if (data.logs && data.logs.length > 0) {
            // Простой способ: просто показываем все логи
            // В реальном проекте лучше отслеживать только новые
            const currentLogs = elements.logContainer.textContent;
            const newLogs = data.logs.join('\n');
            // Обновляем логи только если они изменились
            if (newLogs !== currentLogs) {
                // Пересоздаём логи (можно улучшить)
                clearLogs();
                data.logs.forEach(line => {
                    const type = line.includes('✅') ? 'success' :
                                line.includes('❌') ? 'error' :
                                line.includes('⚠️') ? 'warning' : 'info';
                    addLog(line, type);
                });
            }
        }
        
        if (data.status === 'completed') {
            clearInterval(state.checkInterval);
            addLog('✅ АНАЛИЗ ЗАВЕРШЁН!', 'success');
            elements.resultSection.style.display = 'block';
            
            if (data.report) {
                elements.downloadReportBtn.dataset.report = data.report;
                elements.downloadReportBtn.dataset.analysisId = analysisId;
            }
            
            finishAnalysis();
        } else if (data.status === 'error') {
            clearInterval(state.checkInterval);
            addLog('❌ ' + (data.error || 'Ошибка анализа'), 'error');
            finishAnalysis();
        }
        
    } catch (error) {
        console.error('Ошибка получения статуса:', error);
    }
}

function finishAnalysis() {
    state.isRunning = false;
    elements.runBtn.disabled = false;
    elements.runBtn.textContent = '🚀 Запустить анализ';
    if (state.checkInterval) {
        clearInterval(state.checkInterval);
        state.checkInterval = null;
    }
}

// ============================================================
// ОТКРЫТИЕ ОТЧЁТА
// ============================================================
elements.openReportBtn.addEventListener('click', () => {
    const mode = getSelectedMode();
    const reportUrl = '/report/' + state.analysisId + '?mode=' + mode;
    window.open(reportUrl, '_blank');
});

elements.downloadReportBtn.addEventListener('click', async function() {
    const analysisId = this.dataset.analysisId;
    if (!analysisId) return;
    
    try {
        const response = await fetch(`/api/report/${analysisId}`);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `report_${analysisId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        alert('Ошибка скачивания: ' + error.message);
    }
});

elements.clearLogsBtn.addEventListener('click', clearLogs);

// ============================================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================================
checkDocker();
addLog('📱 APK Analyzer запущен');
addLog('💡 Загрузите APK файл для начала анализа');

// Проверяем Docker каждые 30 секунд
setInterval(checkDocker, 30000);