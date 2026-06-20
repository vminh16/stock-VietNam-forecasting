// State Variables
let currentTheme = localStorage.getItem('theme') || 'dark';
let activeModel = null;
let currentSymbol = null;
let currentDataFile = null;
let availableFiles = [];
let rankedStocks = [];
let globalCandles = []; // Cache for hover calculations

// DOM Elements
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const modelSelect = document.getElementById('model-select');
const deviceSelect = document.getElementById('device-select');
const loadModelBtn = document.getElementById('load-model-btn');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const stockSelect = document.getElementById('stock-select');
const startDateInput = document.getElementById('start-date-input');
const tempInput = document.getElementById('temp-input');
const tempVal = document.getElementById('temp-val');
const topPInput = document.getElementById('topp-input');
const toppVal = document.getElementById('topp-val');
const samplesInput = document.getElementById('samples-input');
const samplesVal = document.getElementById('samples-val');
const predictBtn = document.getElementById('predict-btn');
const scanBtn = document.getElementById('scan-btn');
const rankingList = document.getElementById('ranking-list');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');

// Risk Metric Elements
const varVal = document.getElementById('var-val');
const volVal = document.getElementById('vol-val');
const confidenceVal = document.getElementById('confidence-val');
const trendText = document.getElementById('trend-text');

// TradingView Info Line Elements
const tvSymbol = document.getElementById('tv-symbol');
const tvOpen = document.getElementById('tv-open');
const tvHigh = document.getElementById('tv-high');
const tvLow = document.getElementById('tv-low');
const tvClose = document.getElementById('tv-close');
const tvChange = document.getElementById('tv-change');
const tvVolume = document.getElementById('tv-volume');
const tvAmount = document.getElementById('tv-amount');

// Initialize Theme
document.documentElement.setAttribute('data-theme', currentTheme);
updateThemeButtonUI();

// Event Listeners
themeToggleBtn.addEventListener('click', toggleTheme);
tempInput.addEventListener('input', () => tempVal.textContent = parseFloat(tempInput.value).toFixed(1));
topPInput.addEventListener('input', () => toppVal.textContent = parseFloat(topPInput.value).toFixed(2));
samplesInput.addEventListener('input', () => samplesVal.textContent = parseInt(samplesInput.value));
loadModelBtn.addEventListener('click', loadModel);
predictBtn.addEventListener('click', () => runPrediction(currentDataFile, startDateInput.value));
scanBtn.addEventListener('click', scanAndRankStocks);

// Theme Toggle Functions
function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
    localStorage.setItem('theme', currentTheme);
    updateThemeButtonUI();
    
    // Redraw charts with correct styling if data exists
    if (globalCandles.length > 0) {
        redrawMainChart();
    }
}

function updateThemeButtonUI() {
    themeToggleBtn.innerHTML = currentTheme === 'dark' 
        ? '☀️ Chế độ Sáng' 
        : '🌙 Chế độ Tối';
}

// Fetch Initial Data
async function initApp() {
    await checkModelStatus();
    await fetchAvailableModels();
    await fetchStockFiles();
}

// Check if Model is already loaded
async function checkModelStatus() {
    try {
        const response = await fetch('/api/model-status');
        const data = await response.json();
        if (data.loaded) {
            statusDot.className = 'status-dot connected';
            statusText.textContent = `Đã tải: ${data.current_model.name} (${data.current_model.device})`;
            activeModel = data.current_model.name;
        } else {
            statusDot.className = 'status-dot';
            statusText.textContent = 'Chưa tải mô hình';
        }
    } catch (error) {
        console.error('Error checking model status:', error);
    }
}

// Get Available Models
async function fetchAvailableModels() {
    try {
        const response = await fetch('/api/available-models');
        const data = await response.json();
        
        modelSelect.innerHTML = '';
        Object.keys(data.models).forEach(key => {
            const m = data.models[key];
            const opt = document.createElement('option');
            opt.value = key;
            opt.textContent = `${m.name} (${m.params})`;
            modelSelect.appendChild(opt);
        });
    } catch (error) {
        console.error('Error fetching models:', error);
    }
}

// Get Stock files in data/
async function fetchStockFiles() {
    try {
        const response = await fetch('/api/data-files');
        const data = await response.json();
        availableFiles = data;
        
        stockSelect.innerHTML = '<option value="">-- Chọn mã cổ phiếu --</option>';
        data.forEach(file => {
            const opt = document.createElement('option');
            opt.value = file.path;
            opt.textContent = file.name.replace('.csv', '');
            stockSelect.appendChild(opt);
        });
        
        stockSelect.addEventListener('change', (e) => {
            if (e.target.value) {
                currentDataFile = e.target.value;
                currentSymbol = e.target.options[e.target.selectedIndex].textContent;
                loadStockData(currentDataFile);
            }
        });
    } catch (error) {
        console.error('Error fetching stock files:', error);
    }
}

// Load Metadata for specific Stock
async function loadStockData(filePath) {
    showLoading('Đang tải dữ liệu cổ phiếu...');
    try {
        const response = await fetch('/api/load-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: filePath })
        });
        
        const data = await response.json();
        if (data.success) {
            // Set default date to end_date - lookback_window
            const endDate = new Date(data.data_info.end_date);
            // Default: predict at the end
            startDateInput.value = data.data_info.start_date.split('T')[0];
        } else {
            alert(data.error || 'Lỗi khi tải cổ phiếu');
        }
    } catch (error) {
        console.error('Error loading stock data:', error);
    } finally {
        hideLoading();
    }
}

// Load Selected Model
async function loadModel() {
    const modelKey = modelSelect.value;
    const device = deviceSelect.value;
    
    showLoading(`Đang tải mô hình ${modelSelect.options[modelSelect.selectedIndex].text}...`);
    try {
        const response = await fetch('/api/load-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_key: modelKey, device: device })
        });
        
        const data = await response.json();
        if (data.success) {
            statusDot.className = 'status-dot connected';
            statusText.textContent = `Đã tải: ${data.model_info.name} (${device})`;
            activeModel = data.model_info.name;
        } else {
            alert(data.error || 'Tải mô hình thất bại');
        }
    } catch (error) {
        console.error('Error loading model:', error);
        alert('Có lỗi xảy ra khi giao tiếp với server');
    } finally {
        hideLoading();
    }
}

// Scan and Rank all Stock Files (Top UP Recommendations)
async function scanAndRankStocks() {
    if (!activeModel) {
        alert('Vui lòng nạp mô hình Kronos trước khi thực hiện Quét Khuyến nghị!');
        return;
    }
    
    showLoading('Đang phân tích quét rổ VN50. Quá trình có thể mất 5-10 giây...');
    try {
        const response = await fetch('/api/rank-stocks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lookback: 126,
                pred_len: 5,
                temperature: parseFloat(tempInput.value),
                top_p: parseFloat(topPInput.value)
            })
        });
        
        const data = await response.json();
        if (data.success) {
            rankedStocks = data.rankings;
            renderRankingSidebar();
            
            // Automatically click the top 1 recommended stock
            if (rankedStocks.length > 0) {
                const top1 = rankedStocks[0];
                selectStockFromRanking(top1.file_path, top1.symbol);
            }
        } else {
            alert(data.error || 'Lỗi quét xếp hạng');
        }
    } catch (error) {
        console.error('Error ranking stocks:', error);
        alert('Lỗi quét xếp hạng cổ phiếu');
    } finally {
        hideLoading();
    }
}

// Draw Ranking Sidebar
function renderRankingSidebar() {
    rankingList.innerHTML = '';
    
    rankedStocks.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = `ranking-item ${currentSymbol === item.symbol ? 'active' : ''}`;
        div.dataset.symbol = item.symbol;
        
        const isUp = item.predicted_return > 0.03;
        const isDown = item.predicted_return < -0.03;
        
        let trendClass = 'trend-sideway';
        let trendText = '● SIDE';
        if (isUp) {
            trendClass = 'trend-up';
            trendText = '▲ TĂNG';
        } else if (isDown) {
            trendClass = 'trend-down';
            trendText = '▼ GIẢM';
        }
        
        const returnText = (item.predicted_return * 100).toFixed(2);
        
        div.innerHTML = `
            <span class="rank-badge">#${index + 1}</span>
            <div class="ticker-info">
                <div class="ticker-symbol">${item.symbol}</div>
                <div class="ticker-change price ${item.predicted_return >= 0 ? 'trend-up' : 'trend-down'}">
                    ${item.predicted_return >= 0 ? '+' : ''}${returnText}%
                </div>
            </div>
            <span class="trend-indicator ${trendClass}">${trendText}</span>
        `;
        
        div.addEventListener('click', () => {
            // Remove active classes
            document.querySelectorAll('.ranking-item').forEach(el => el.classList.remove('active'));
            div.classList.add('active');
            selectStockFromRanking(item.file_path, item.symbol);
        });
        
        rankingList.appendChild(div);
    });
}

// Click on Sidebar stock
async function selectStockFromRanking(filePath, symbol) {
    currentDataFile = filePath;
    currentSymbol = symbol;
    
    // Update select dropdown
    for (let option of stockSelect.options) {
        if (option.textContent === symbol) {
            stockSelect.value = option.value;
            break;
        }
    }
    
    // Auto-predict that stock
    await runPrediction(filePath, '');
}

// Run Prediction for Selected Stock
async function runPrediction(filePath, startDate) {
    if (!filePath) {
        alert('Vui lòng chọn cổ phiếu trước!');
        return;
    }
    if (!activeModel) {
        alert('Vui lòng nạp mô hình Kronos trước!');
        return;
    }
    
    showLoading(`Đang sinh dự báo cho mã ${currentSymbol}...`);
    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_path: filePath,
                lookback: 126,
                pred_len: 5,
                temperature: parseFloat(tempInput.value),
                top_p: parseFloat(topPInput.value),
                sample_count: parseInt(samplesInput.value),
                start_date: startDate || null
            })
        });
        
        const data = await response.json();
        if (data.success) {
            renderDashboardResults(data);
        } else {
            alert(data.error || 'Dự báo thất bại');
        }
    } catch (error) {
        console.error('Error predicting:', error);
        alert('Lỗi trong quá trình suy luận mô hình');
    } finally {
        hideLoading();
    }
}

// Render Results to UI (Chart, Info Line, Risk, XAI)
let lastChartData = null; // Cache to handle theme changes

function renderDashboardResults(data) {
    // 1. Render Risk Indicators
    const risk = data.risk_metrics;
    
    varVal.textContent = risk.var_5pct.toFixed(2);
    volVal.textContent = (risk.volatility * 100).toFixed(2) + '%';
    confidenceVal.textContent = risk.confidence_width.toFixed(2);
    
    // Apply conditional coloring for Risk
    if (risk.volatility > 0.05) {
        volVal.className = 'risk-metric-value risk-high';
    } else {
        volVal.className = 'risk-metric-value risk-low';
    }
    
    // Render Trend Card
    const trend = data.trend;
    trendText.textContent = trend.trend_class;
    trendText.className = 'trend-indicator';
    if (trend.trend_class === 'UP') {
        trendText.classList.add('trend-up');
    } else if (trend.trend_class === 'DOWN') {
        trendText.classList.add('trend-down');
    } else {
        trendText.classList.add('trend-sideway');
    }
    
    // 2. Cache candles for hover line
    globalCandles = data.raw_candles; // Array of {timestamp, open, high, low, close, volume, amount}
    lastChartData = data;
    
    // Update TV Symbol Header
    tvSymbol.textContent = currentSymbol;
    
    // Set initial TV Info Line values to the last candle
    if (globalCandles.length > 0) {
        updateTVInfoLine(globalCandles[globalCandles.length - 1]);
    }
    
    // 3. Render Main Candlestick Chart (Plotly)
    redrawMainChart();
    
    // 4. Render XAI Token Chart
    renderXAIChart(data.xai_data);
}

// Redraw main chart based on active theme
function redrawMainChart() {
    if (!lastChartData) return;
    
    const chartDiv = document.getElementById('main-chart');
    const isDark = currentTheme === 'dark';
    
    const layoutColors = {
        bg: isDark ? '#161b22' : '#ffffff',
        grid: isDark ? '#30363d' : '#e1e4e6',
        text: isDark ? '#c9d1d9' : '#1f2328',
        candleUp: isDark ? '#26a69a' : '#2da44e',
        candleDown: isDark ? '#ef5350' : '#cf222e',
        stochastic: isDark ? 'rgba(88, 166, 255, 0.04)' : 'rgba(9, 105, 218, 0.04)',
        stochasticMean: isDark ? '#58a6ff' : '#0969da'
    };
    
    const raw = lastChartData.raw_candles;
    
    // Parse series
    const dates = raw.map(c => c.timestamp);
    const opens = raw.map(c => c.open);
    const highs = raw.map(c => c.high);
    const lows = raw.map(c => c.low);
    const closes = raw.map(c => c.close);
    
    // Separate into historical and actual segments
    const predLen = lastChartData.prediction_results.length;
    const historyLen = raw.length - predLen;
    
    const datesHist = dates.slice(0, historyLen);
    const opensHist = opens.slice(0, historyLen);
    const highsHist = highs.slice(0, historyLen);
    const lowsHist = lows.slice(0, historyLen);
    const closesHist = closes.slice(0, historyLen);
    
    const datesPred = dates.slice(historyLen);
    
    // Traces list
    const traces = [];
    
    // Trace 1: Historical candles
    traces.push({
        x: datesHist,
        open: opensHist,
        high: highsHist,
        low: lowsHist,
        close: closesHist,
        type: 'candlestick',
        name: 'Lịch sử',
        increasing: { line: { color: layoutColors.candleUp }, fillcolor: layoutColors.candleUp },
        decreasing: { line: { color: layoutColors.candleDown }, fillcolor: layoutColors.candleDown },
        hoverinfo: 'none' // We use custom status bar hover
    });
    
    // Trace 2: Actual candles (if exists)
    if (lastChartData.has_comparison) {
        const opensAct = opens.slice(historyLen);
        const highsAct = highs.slice(historyLen);
        const lowsAct = lows.slice(historyLen);
        const closesAct = closes.slice(historyLen);
        
        traces.push({
            x: datesPred,
            open: opensAct,
            high: highsAct,
            low: lowsAct,
            close: closesAct,
            type: 'candlestick',
            name: 'Thực tế',
            increasing: { line: { color: '#ff9800' }, fillcolor: '#ff9800' },
            decreasing: { line: { color: '#f44336' }, fillcolor: '#f44336' },
            hoverinfo: 'none'
        });
    }
    
    // Trace 3: Stochastic Sample Paths (represented as line paths)
    const paths = lastChartData.stochastic_paths; // Shape: [sample_count, pred_len, features]
    if (paths && paths.length > 0) {
        // Last close of history is the starting point for predictions
        const lastHistClose = closesHist[closesHist.length - 1];
        const lastHistDate = datesHist[datesHist.length - 1];
        
        const pathDates = [lastHistDate, ...datesPred];
        
        paths.forEach((path, pIdx) => {
            const pathCloses = [lastHistClose, ...path.map(c => c[3])]; // Index 3 is Close
            
            traces.push({
                x: pathDates,
                y: pathCloses,
                mode: 'lines',
                line: {
                    color: layoutColors.stochastic,
                    width: 1
                },
                name: pIdx === 0 ? 'Stochastic Paths' : `Path ${pIdx}`,
                showlegend: pIdx === 0,
                hoverinfo: 'none'
            });
        });
    }
    
    // Trace 4: Prediction Mean line
    const opensPred = lastChartData.prediction_results.map(c => c.open);
    const closesPred = lastChartData.prediction_results.map(c => c.close);
    const lastHistClose = closesHist[closesHist.length - 1];
    const lastHistDate = datesHist[datesHist.length - 1];
    
    traces.push({
        x: [lastHistDate, ...datesPred],
        y: [lastHistClose, ...closesPred],
        mode: 'lines+markers',
        line: {
            color: layoutColors.stochasticMean,
            width: 3,
            dash: 'dash'
        },
        marker: { size: 6 },
        name: 'Trung bình dự báo (Mean)',
        hoverinfo: 'none'
    });
    
    const layout = {
        margin: { t: 10, b: 40, l: 50, r: 20 },
        plot_bgcolor: layoutColors.bg,
        paper_bgcolor: layoutColors.bg,
        xaxis: {
            gridcolor: layoutColors.grid,
            tickcolor: layoutColors.grid,
            tickfont: { color: layoutColors.text },
            rangeslider: { visible: false },
            type: 'date'
        },
        yaxis: {
            gridcolor: layoutColors.grid,
            tickcolor: layoutColors.grid,
            tickfont: { color: layoutColors.text },
            title: { text: 'Giá', font: { color: layoutColors.text } }
        },
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: 1.02,
            xanchor: 'right',
            x: 1,
            font: { color: layoutColors.text }
        },
        hovermode: 'x unified',
        showlegend: true
    };
    
    Plotly.newPlot(chartDiv, traces, layout, { responsive: true, displayModeBar: false });
    
    // Hover event to update TradingView-style Info Line
    chartDiv.on('plotly_hover', function(data) {
        if (!data || !data.points || data.points.length === 0) return;
        
        // Find corresponding candle by timestamp
        const hoveredDate = data.points[0].x;
        const matchingCandle = globalCandles.find(c => c.timestamp === hoveredDate);
        
        if (matchingCandle) {
            // Find previous close to calculate change
            const curIdx = globalCandles.indexOf(matchingCandle);
            let prevClose = matchingCandle.open;
            if (curIdx > 0) {
                prevClose = globalCandles[curIdx - 1].close;
            }
            updateTVInfoLine(matchingCandle, prevClose);
        }
    });
    
    // Unhover event resets to last candle info
    chartDiv.on('plotly_unhover', function() {
        if (globalCandles.length > 0) {
            updateTVInfoLine(globalCandles[globalCandles.length - 1]);
        }
    });
}

// Update TradingView status bar HTML
function updateTVInfoLine(candle, prevClose = null) {
    if (!candle) return;
    
    tvOpen.textContent = candle.open.toLocaleString();
    tvHigh.textContent = candle.high.toLocaleString();
    tvLow.textContent = candle.low.toLocaleString();
    tvClose.textContent = candle.close.toLocaleString();
    
    // Calculate Change
    const checkPrev = prevClose !== null ? prevClose : candle.open;
    const diff = candle.close - checkPrev;
    const pct = (diff / checkPrev) * 100;
    
    const formattedDiff = (diff >= 0 ? '+' : '') + diff.toLocaleString();
    const formattedPct = (diff >= 0 ? '+' : '') + pct.toFixed(2) + '%';
    
    tvChange.textContent = `${formattedDiff} (${formattedPct})`;
    
    // Update color classes based on sign
    const ohlcItems = [tvOpen, tvHigh, tvLow, tvClose];
    if (diff >= 0) {
        tvChange.className = 'tv-change-val price trend-up';
        ohlcItems.forEach(item => item.parentElement.className = 'tv-ohlc-item up');
    } else {
        tvChange.className = 'tv-change-val price trend-down';
        ohlcItems.forEach(item => item.parentElement.className = 'tv-ohlc-item down');
    }
    
    // Format Volume and Amount (Billion VND helper)
    let volText = candle.volume.toLocaleString();
    if (candle.volume >= 1000000) {
        volText = (candle.volume / 1000000).toFixed(2) + 'M';
    }
    tvVolume.textContent = volText;
    
    let amtText = candle.amount.toLocaleString();
    if (candle.amount >= 1000000000) {
        amtText = (candle.amount / 1000000000).toFixed(2) + 'B';
    }
    tvAmount.textContent = amtText;
}

// Render XAI Bar Chart
function renderXAIChart(xaiData) {
    const xaiChartDiv = document.getElementById('xai-chart');
    const isDark = currentTheme === 'dark';
    
    const layoutColors = {
        bg: isDark ? '#161b22' : '#ffffff',
        text: isDark ? '#c9d1d9' : '#1f2328',
        bar: isDark ? '#3b82f6' : '#0969da'
    };
    
    if (!xaiData || xaiData.length === 0) {
        xaiChartDiv.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding-top:50px;">Không có dữ liệu giải thích XAI</div>';
        return;
    }
    
    // Limit to top 10 tokens
    const topXAI = xaiData.slice(0, 10);
    const tokens = topXAI.map(d => `Token #${d.token}`);
    const freqs = topXAI.map(d => d.frequency);
    
    const trace = {
        x: freqs,
        y: tokens,
        type: 'bar',
        orientation: 'h',
        marker: { color: layoutColors.bar },
        hoverinfo: 'x'
    };
    
    const layout = {
        margin: { t: 5, b: 30, l: 80, r: 20 },
        plot_bgcolor: layoutColors.bg,
        paper_bgcolor: layoutColors.bg,
        xaxis: {
            tickfont: { color: layoutColors.text, size: 10 },
            gridcolor: isDark ? '#30363d' : '#e1e4e6'
        },
        yaxis: {
            tickfont: { color: layoutColors.text, size: 10 },
            autorange: 'reversed'
        },
        showlegend: false
    };
    
    Plotly.newPlot(xaiChartDiv, [trace], layout, { responsive: true, displayModeBar: false });
}

// Show/Hide Loading Overlay
function showLoading(text) {
    loadingText.textContent = text;
    loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
}

// Initialize Application
initApp();
