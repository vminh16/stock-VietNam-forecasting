// State Variables
let currentTab = 'overview';
let activeModel = null;
let currentSymbol = null;
let currentDataFile = null;
let allStocks = []; // Full rankings list with enriched metadata
let watchlist = JSON.parse(localStorage.getItem('watchlist')) || ['VCB', 'HPG', 'FPT', 'VHM'];
let theme = localStorage.getItem('theme') || 'dark';
let tableDensity = localStorage.getItem('tableDensity') || 'compact';

// Table Display Limits
let overviewLimit = 25;
let activeSectorFilter = 'Tất cả';
let activeTrendFilter = null;

// Chart Instances
let detailsChart = null;
let detailsCandleSeries = null;
let detailsMeanSeries = null;
let detailsStochasticSeriesList = [];
let detailsVar5Series = null;
let detailsVar95Series = null;
let detailsCeilSeries = null;
let detailsFloorSeries = null;

let heroChart = null;
let heroAreaSeries = null;

let backtestChart = null;

// DOM Elements
const sidebarSearch = document.getElementById('sidebar-search-input');
const navItems = document.querySelectorAll('.nav-item');
const tabContents = document.querySelectorAll('.tab-content');
const currentTabTitle = document.getElementById('current-tab-title');
const marketStatusDot = document.querySelector('.market-status-dot');

const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');

// DOM Elements mới cho predict-all
const inferenceWarningBanner = document.getElementById('inference-warning-banner');
const bannerPredictAllBtn = document.getElementById('banner-predict-all-btn');
const settingsPredictAllBtn = document.getElementById('settings-predict-all-btn');

let needsInference = false;
let reportsData = null;

// Settings Elements
const modelSelect = document.getElementById('model-select');
const deviceSelect = document.getElementById('device-select');
const loadModelBtn = document.getElementById('load-model-btn');
const stockSelect = document.getElementById('stock-select');
const startDateInput = document.getElementById('start-date-input');
const tempInput = document.getElementById('temp-input');
const tempVal = document.getElementById('temp-val');
const topPInput = document.getElementById('topp-input');
const toppVal = document.getElementById('topp-val');
const samplesInput = document.getElementById('samples-input');
const samplesVal = document.getElementById('samples-val');
const predictBtn = document.getElementById('predict-btn');

// Overview Elements
const countsUp = document.getElementById('counts-up');
const countsDown = document.getElementById('counts-down');
const countsSide = document.getElementById('counts-side');
const avgUp = document.getElementById('avg-up');
const avgDown = document.getElementById('avg-down');
const avgSide = document.getElementById('avg-side');
const tileUp = document.getElementById('tile-up');
const tileDown = document.getElementById('tile-down');
const tileSideway = document.getElementById('tile-sideway');
const sectorTabs = document.getElementById('sector-tabs');
const overviewTableBody = document.getElementById('overview-table-body');
const overviewTableCount = document.getElementById('overview-table-count');
const overviewLoadMore = document.getElementById('overview-load-more');

// Hero Stock Elements
const heroStockSymbol = document.getElementById('hero-stock-symbol');
const heroStockExchange = document.getElementById('hero-stock-exchange');
const heroStockName = document.getElementById('hero-stock-name');
const heroStockPrice = document.getElementById('hero-stock-price');
const heroStockChange = document.getElementById('hero-stock-change');
const heroTargetPrice = document.getElementById('hero-target-price');
const heroTargetReturn = document.getElementById('hero-target-return');
const heroVolatility = document.getElementById('hero-volatility');
const heroTrendIndicator = document.getElementById('hero-trend-indicator');
const heroConfidenceDots = document.getElementById('hero-confidence-dots');

// Screener Elements
const screenerSectorSelect = document.getElementById('screener-sector-select');
const screenerTrendGroup = document.getElementById('screener-trend-group');
const screenerConfSlider = document.getElementById('screener-conf-slider');
const screenerConfLbl = document.getElementById('screener-conf-lbl');
const screenerRiskSlider = document.getElementById('screener-risk-slider');
const screenerRiskLbl = document.getElementById('screener-risk-lbl');
const screenerMatchCount = document.getElementById('screener-match-count');
const screenerTableBody = document.getElementById('screener-table-body');

// Watchlist Elements
const watchlistGrid = document.getElementById('watchlist-grid');
const watchlistAddForm = document.getElementById('watchlist-add-form');
const watchlistAddInput = document.getElementById('watchlist-add-input');
const watchlistTotalDatabase = document.getElementById('watchlist-total-database');
const watchlistTrendBars = document.getElementById('watchlist-trend-bars');
const watchlistRiskBars = document.getElementById('watchlist-risk-bars');
const watchlistAlertsList = document.getElementById('watchlist-alerts-list');

// Details Elements
const detailsBreadcrumbSymbol = document.getElementById('details-breadcrumb-symbol');
const detailsStockLogoLetters = document.getElementById('details-stock-logo-letters');
const detailsStockSymbol = document.getElementById('details-stock-symbol');
const detailsStockExchange = document.getElementById('details-stock-exchange');
const detailsCeilingFloorBadgeContainer = document.getElementById('details-ceiling-floor-badge-container');
const detailsStockName = document.getElementById('details-stock-name');
const detailsStockPrice = document.getElementById('details-stock-price');
const detailsStockChange = document.getElementById('details-stock-change');
const detailsRefPrice = document.getElementById('details-ref-price');
const detailsCeilPrice = document.getElementById('details-ceil-price');
const detailsFloorPrice = document.getElementById('details-floor-price');
const detailsTrendBadgeContainer = document.getElementById('details-trend-badge-container');
const detailsConfidenceDots = document.getElementById('details-confidence-dots');
const detailsConfidenceText = document.getElementById('details-confidence-text');

// TradingView details bar
const detailsChartSymbol = document.getElementById('details-chart-symbol');
const detailsTvOpen = document.getElementById('details-tv-open');
const detailsTvHigh = document.getElementById('details-tv-high');
const detailsTvLow = document.getElementById('details-tv-low');
const detailsTvClose = document.getElementById('details-tv-close');
const detailsTvChange = document.getElementById('details-tv-change');
const detailsTvVolume = document.getElementById('details-tv-volume');
const detailsTvAmount = document.getElementById('details-tv-amount');

// Detailed Risk Elements
const detailsRiskScore = document.getElementById('details-risk-score');
const detailsF5Close = document.getElementById('details-f5-close');
const detailsF5Pct = document.getElementById('details-f5-pct');
const detailsGradientPointer = document.getElementById('details-gradient-pointer');
const detailsGradientLow = document.getElementById('details-gradient-low');
const detailsGradientHigh = document.getElementById('details-gradient-high');
const detailsGradientSpread = document.getElementById('details-gradient-spread');
const detailsProbUpVal = document.getElementById('details-prob-up-val');
const detailsProbSideVal = document.getElementById('details-prob-side-val');
const detailsProbDownVal = document.getElementById('details-prob-down-val');
const detailsProbUpBar = document.getElementById('details-prob-up-bar');
const detailsProbSideBar = document.getElementById('details-prob-side-bar');
const detailsProbDownBar = document.getElementById('details-prob-down-bar');
const detailsT2Date = document.getElementById('details-t2-date');
const detailsRiskGaugeContainer = document.getElementById('details-risk-gauge-container');

// Subtabs
const detailsSubTabs = document.querySelectorAll('.sub-tab');
const subTabContents = document.querySelectorAll('.sub-tab-content');
const detailsForecastTableBody = document.getElementById('details-forecast-table-body');
const detailsHistoryTableBody = document.getElementById('details-history-table-body');
const detailsXaiPatterns = document.getElementById('details-xai-patterns');
const detailsXaiTimeline = document.getElementById('details-xai-timeline');
const xaiHeaderTitle = document.getElementById('xai-header-title');

// Backtest & Logs Elements
const backtestTableBody = document.getElementById('backtest-table-body');
const backtestDailyCards = document.getElementById('backtest-daily-cards');
const logsTableBody = document.getElementById('logs-table-body');

// Loader Overlay
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');

// Theme Elements
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const themeIcon = document.getElementById('theme-icon');
const settingsThemeSelect = document.getElementById('settings-theme-select');

// Sector List static definition matching Python side
const SECTOR_LIST = ["Tất cả", "Ngân hàng", "Thép", "Bất động sản", "Công nghệ", "Bán lẻ & TD", "Dầu khí", "Chứng khoán", "Hóa chất", "Hàng không", "Điện", "Cao su", "Xây dựng", "Thủy sản", "Bảo hiểm"];

// Baseline Backtest mock data matching React performance page
const WALK_FORWARD_DATA = [
    { fold: '2021', kronosFT: 53.1, kronosZS: 51.2, naive: 50.1, sma: 49.8 },
    { fold: '2022', kronosFT: 55.4, kronosZS: 52.3, naive: 50.4, sma: 50.1 },
    { fold: '2023', kronosFT: 54.0, kronosZS: 51.8, naive: 50.2, sma: 49.5 },
    { fold: '2024', kronosFT: 56.2, kronosZS: 53.1, naive: 49.9, sma: 50.3 },
    { fold: '2025', kronosFT: 54.3, kronosZS: 52.0, naive: 50.0, sma: 49.7 },
];

const DAILY_LOG_DATA = [
    { date: "Thứ 2 — 09/06/2026", predicted: "TĂNG", actual: "TĂNG", da: 68, correct: 34, total: 50 },
    { date: "Thứ 3 — 10/06/2026", predicted: "GIẢM", actual: "GIẢM", da: 62, correct: 31, total: 50 },
    { date: "Thứ 4 — 11/06/2026", predicted: "TĂNG", actual: "ĐI NGANG", da: 48, correct: 24, total: 50 },
    { date: "Thứ 5 — 12/06/2026", predicted: "TĂNG", actual: "TĂNG", da: 56, correct: 28, total: 50 },
    { date: "Thứ 6 — 13/06/2026", predicted: "GIẢM", actual: "GIẢM", da: 64, correct: 32, total: 50 },
    { date: "Thứ 2 — 16/06/2026", predicted: "TĂNG", actual: "TĂNG", da: 60, correct: 30, total: 50 },
    { date: "Thứ 3 — 17/06/2026", predicted: "ĐI NGANG", actual: "TĂNG", da: 50, correct: 25, total: 50 },
];

// Initialize Application Theme
document.documentElement.setAttribute('data-theme', theme);
updateThemeUI();

// Event Listeners for Theme Switching
themeToggleBtn.addEventListener('click', toggleTheme);
settingsThemeSelect.addEventListener('change', () => {
    theme = settingsThemeSelect.value;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    updateThemeUI();
    // Redraw charts
    if (currentSymbol) {
        runPredictForDetails(currentSymbol, false);
    }
    renderBacktestFoldChart();
});

// Event Listeners for Tab Navigation
navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const targetTab = item.getAttribute('data-tab');
        switchTab(targetTab);
    });
});

// Input Value Bindings
tempInput.addEventListener('input', () => tempVal.textContent = parseFloat(tempInput.value).toFixed(1));
topPInput.addEventListener('input', () => toppVal.textContent = parseFloat(topPInput.value).toFixed(2));
samplesInput.addEventListener('input', () => samplesVal.textContent = parseInt(samplesInput.value));

// Model buttons
loadModelBtn.addEventListener('click', loadModel);
predictBtn.addEventListener('click', () => {
    if (stockSelect.value) {
        const symbol = stockSelect.options[stockSelect.selectedIndex].text;
        switchTab('details');
        runPredictForDetails(symbol, true);
    }
});

// Sidebar search redirector
sidebarSearch.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const query = sidebarSearch.value.trim().toUpperCase();
        if (query.length > 0) {
            sidebarSearch.value = '';
            switchTab('details');
            runPredictForDetails(query, true);
        }
    }
});

// Overview tab listeners
tileUp.addEventListener('click', () => toggleTrendFilter('up'));
tileDown.addEventListener('click', () => toggleTrendFilter('down'));
tileSideway.addEventListener('click', () => toggleTrendFilter('sideway'));

overviewLoadMore.addEventListener('click', () => {
    overviewLimit += 25;
    renderMarketTable();
});

// Table Density Toggle Listeners & Initialization
const tableDensityBtn = document.getElementById('table-density-btn');
const densityBtnText = document.getElementById('density-btn-text');

if (tableDensityBtn) {
    updateDensityUI();
    tableDensityBtn.addEventListener('click', () => {
        tableDensity = tableDensity === 'compact' ? 'relaxed' : 'compact';
        localStorage.setItem('tableDensity', tableDensity);
        updateDensityUI();
    });
}

function updateDensityUI() {
    const marketTable = document.getElementById('market-table');
    const screenerTable = document.getElementById('screener-table');
    const logsTable = document.getElementById('logs-table');
    
    if (tableDensity === 'relaxed') {
        if (marketTable) marketTable.classList.add('density-relaxed');
        if (screenerTable) screenerTable.classList.add('density-relaxed');
        if (logsTable) logsTable.classList.add('density-relaxed');
    } else {
        if (marketTable) marketTable.classList.remove('density-relaxed');
        if (screenerTable) screenerTable.classList.remove('density-relaxed');
        if (logsTable) logsTable.classList.remove('density-relaxed');
    }
    
    if (tableDensityBtn) {
        const icon = tableDensity === 'compact' ? 'stretch-horizontal' : 'minimize-2';
        tableDensityBtn.innerHTML = `<i data-lucide="${icon}"></i> <span id="density-btn-text">${tableDensity === 'compact' ? 'Giãn rộng bảng' : 'Thu nhỏ bảng'}</span>`;
        lucide.createIcons({ node: tableDensityBtn });
    }
}

// Screener listeners
screenerSectorSelect.addEventListener('change', runScreenerFiltering);
screenerConfSlider.addEventListener('input', () => {
    screenerConfLbl.textContent = `Tin cậy tối thiểu: ${screenerConfSlider.value}/5`;
    runScreenerFiltering();
});
screenerRiskSlider.addEventListener('input', () => {
    screenerRiskLbl.textContent = `Rủi ro tối đa: ${screenerRiskSlider.value}/100`;
    runScreenerFiltering();
});
document.querySelectorAll('#screener-trend-group .btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('#screener-trend-group .btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        runScreenerFiltering();
    });
});

// Watchlist Add Listener
watchlistAddForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const sym = watchlistAddInput.value.trim().toUpperCase();
    watchlistAddInput.value = '';
    if (sym.length > 0) {
        // Validate if stock exists in database
        const exists = allStocks.some(s => s.symbol === sym);
        if (exists && !watchlist.includes(sym)) {
            watchlist.push(sym);
            localStorage.setItem('watchlist', JSON.stringify(watchlist));
            renderWatchlistTab();
        } else if (!exists) {
            showToast(`Mã cổ phiếu ${sym} không tồn tại trong cơ sở dữ liệu rổ VN50.`, 'warning');
        }
    }
});

// Back breadcrumb
document.getElementById('back-to-overview-link').addEventListener('click', (e) => {
    e.preventDefault();
    switchTab('overview');
});

// Details subtabs handler
detailsSubTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        detailsSubTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const sub = tab.getAttribute('data-subtab');
        subTabContents.forEach(c => c.classList.remove('active'));
        document.getElementById(`subtab-${sub}`).classList.add('active');
    });
});

// Toast System
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast-item ${type}`;
    
    let iconName = 'info';
    if (type === 'success') iconName = 'check-circle';
    else if (type === 'error') iconName = 'alert-octagon';
    else if (type === 'warning') iconName = 'alert-triangle';
    
    const vnTitles = {
        'success': 'Thành công',
        'error': 'Lỗi',
        'warning': 'Cảnh báo',
        'info': 'Thông tin'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">
            <i data-lucide="${iconName}"></i>
        </div>
        <div class="toast-content">
            <span class="toast-title">${vnTitles[type] || 'Thông tin'}</span>
            <span class="toast-message">${message.replace(/\n/g, '<br>')}</span>
        </div>
        <button class="toast-close">&times;</button>
    `;
    
    container.appendChild(toast);
    lucide.createIcons({
        attrs: {
            class: 'lucide-icon'
        },
        node: toast
    });
    
    const closeBtn = toast.querySelector('.toast-close');
    const dismissToast = () => {
        toast.classList.add('hide');
        setTimeout(() => {
            toast.remove();
        }, 300);
    };
    
    closeBtn.addEventListener('click', dismissToast);
    setTimeout(dismissToast, 4000);
}

// PDF Report button mock click
document.getElementById('pdf-report-btn').addEventListener('click', () => {
    showToast(`Đang khởi tạo tải báo cáo phân tích PDF cho mã ${currentSymbol}...\nDự báo 5 phiên, phân tích rủi ro VaR và thống kê S1 Token.\nTập tin phân tích sẵn sàng tải xuống.`, 'success');
});

// Price alert mock click
document.getElementById('set-price-alert-btn').addEventListener('click', () => {
    const alertVal = prompt(`Đặt mức giá cảnh báo cho mã ${currentSymbol} (đơn vị ₫):`, Math.round(allStocks.find(s => s.symbol === currentSymbol)?.current_close || 50000));
    if (alertVal) {
        showToast(`Đã kích hoạt cảnh báo giá! Hệ thống sẽ thông báo khi ${currentSymbol} đạt mức ${parseInt(alertVal).toLocaleString()} ₫.`, 'success');
    }
});

// Helpers
function formatPrice(val) {
    if (val === undefined || val === null) return '--';
    return Math.round(val).toLocaleString('vi-VN');
}

function formatPct(val) {
    if (val === undefined || val === null) return '--%';
    return (val >= 0 ? '+' : '') + val.toFixed(2) + '%';
}

function formatVolume(val) {
    if (val === undefined || val === null) return '--';
    if (val >= 1000000) {
        return (val / 1000000).toFixed(2) + 'M';
    }
    return Math.round(val).toLocaleString();
}

function formatAmount(val) {
    if (val === undefined || val === null) return '--';
    if (val >= 1000000000) {
        return (val / 1000000000).toFixed(2) + 'B';
    }
    return Math.round(val).toLocaleString();
}

function formatVnDate(dateStr) {
    const d = new Date(dateStr);
    return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function formatVnDateLong(dateStr) {
    const d = new Date(dateStr);
    const dayNames = ["Chủ nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"];
    return `${dayNames[d.getDay()]} — ${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
}

function getThemeColors() {
    const isDark = (theme === 'dark');
    return {
        background: isDark ? '#0d1117' : '#ffffff',
        grid: isDark ? '#21262d' : '#f0f0f0',
        text: isDark ? '#8b949e' : '#57606a',
        candleUp: '#089981',
        candleDown: '#f23645',
        stochastic: isDark ? 'rgba(56, 139, 253, 0.12)' : 'rgba(9, 105, 218, 0.12)',
        meanPath: isDark ? '#00f0ff' : '#2962ff',
        var5: '#f23645',
        var95: '#089981',
        ceiling: '#bf8eff',
        floor: '#56d6ff'
    };
}

// UI Mode switches
function toggleTheme() {
    theme = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    settingsThemeSelect.value = theme;
    updateThemeUI();
    // Re-render current chart
    if (currentSymbol) {
        runPredictForDetails(currentSymbol, false);
    }
    // Re-render hero recommendation chart
    if (allStocks && allStocks.length > 0) {
        renderHeroChart(allStocks[0]);
    }
    renderBacktestFoldChart();
}

function updateThemeUI() {
    const iconName = theme === 'dark' ? 'moon' : 'sun';
    themeToggleBtn.innerHTML = `<i data-lucide="${iconName}" id="theme-icon"></i>`;
    settingsThemeSelect.value = theme;
    lucide.createIcons();
}

// Switch between view tabs
function switchTab(tabId) {
    currentTab = tabId;
    
    // Update sidebar UI active state
    navItems.forEach(item => {
        if (item.getAttribute('data-tab') === tabId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Toggle tab panels visibility
    tabContents.forEach(content => {
        if (content.id === `tab-${tabId}`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });

    // Update Header Tab Title
    const titles = {
        'overview': 'Tổng quan thị trường',
        'screener': 'Sàng lọc cổ phiếu VN50',
        'watchlist': 'Danh mục theo dõi cá nhân',
        'details': `Chi tiết & Dự báo AI — ${currentSymbol || 'Chưa chọn mã'}`,
        'backtest': 'Hiệu suất Kiểm thử ngược (Walk-Forward)',
        'logs': 'Nhật ký Dự báo & Đối chiếu thực tế',
        'settings': 'Cấu hình hệ thống'
    };
    currentTabTitle.textContent = titles[tabId] || 'Hệ thống Kronos';

    // Handle lazy chart resizing on visibility
    if (tabId === 'details' && detailsChart) {
        const container = document.getElementById('details-forecast-chart');
        if (container) {
            detailsChart.resize(container.clientWidth, 430);
        }
    } else if (tabId === 'backtest' && backtestChart) {
        const container = document.getElementById('backtest-fold-chart');
        if (container) {
            backtestChart.resize(container.clientWidth, 280);
        }
    } else if (tabId === 'overview' && heroChart) {
        const container = document.getElementById('hero-recommendation-chart');
        if (container) {
            heroChart.resize(container.clientWidth, 200);
        }
    }

    lucide.createIcons();
}

// Initial API Load
async function initApp() {
    showLoading('Đang khởi tạo hệ thống...');
    try {
        await checkModelStatus();
        await fetchAvailableModels();
        await loadPerformanceReports();
        
        // 1. Tải dữ liệu lịch sử thô trước
        let basicStocks = [];
        try {
            const stocksRes = await fetch('/api/stocks');
            const stocksData = await stocksRes.json();
            if (stocksData.success) {
                basicStocks = stocksData.stocks;
            }
        } catch (err) {
            console.error('Failed to load raw stocks:', err);
        }
        
        // 2. Kiểm tra cache dự báo
        const response = await fetch('/api/rank-stocks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lookback: 126,
                pred_len: 5,
                temperature: 1.0,
                top_p: 0.9
            })
        });
        const data = await response.json();
        if (data.success) {
            const cacheTag = document.getElementById('cache-info-tag');
            const cacheText = document.getElementById('cache-info-text');
            
            if (data.needs_inference) {
                needsInference = true;
                allStocks = basicStocks;
                if (inferenceWarningBanner) {
                    inferenceWarningBanner.style.display = 'flex';
                }
                if (cacheTag) cacheTag.style.display = 'none';
            } else {
                needsInference = false;
                allStocks = data.rankings;
                if (inferenceWarningBanner) {
                    inferenceWarningBanner.style.display = 'none';
                }
                if (cacheTag && cacheText && data.cache_date) {
                    cacheText.textContent = `Dự báo phiên: ${data.cache_date}`;
                    cacheTag.style.display = 'inline-flex';
                    showToast(`Đã tự động nạp dữ liệu dự báo từ cache phiên giao dịch: ${data.cache_date}`, 'success');
                } else if (cacheTag) {
                    cacheTag.style.display = 'none';
                }
            }
            
            watchlistTotalDatabase.textContent = allStocks.length;
            
            // Populating stock selects in configs
            stockSelect.innerHTML = '';
            allStocks.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.symbol;
                opt.textContent = s.symbol;
                stockSelect.appendChild(opt);
            });
            
            // Populate screener sector options
            screenerSectorSelect.innerHTML = '<option>Tất cả</option>';
            SECTOR_LIST.slice(1).forEach(s => {
                const opt = document.createElement('option');
                opt.value = s;
                opt.textContent = s;
                screenerSectorSelect.appendChild(opt);
            });

            // Set default stock file reference
            const defaultStock = allStocks.find(s => s.symbol === 'VCB') || allStocks[0];
            if (defaultStock) {
                currentSymbol = defaultStock.symbol;
            }
            
            // Run prediction for the Top 1 stock to fill Hero card if cache exists
            if (allStocks.length > 0 && !needsInference) {
                const top1 = allStocks[0];
                updateHeroCard(top1);
            } else if (allStocks.length > 0 && needsInference) {
                heroStockSymbol.textContent = "--";
                heroStockName.textContent = "Chưa chạy dự báo. Vui lòng bấm chạy dự báo rổ.";
                heroStockPrice.textContent = "-- ₫";
                heroStockChange.textContent = "--";
                heroTargetPrice.textContent = "-- ₫";
                heroTargetReturn.textContent = "--";
                heroVolatility.textContent = "--";
                heroTrendIndicator.textContent = "--";
                heroConfidenceDots.innerHTML = "";
                
                const container = document.getElementById('hero-recommendation-chart');
                if (container) {
                    container.innerHTML = '<div class="chart-placeholder">Chưa có dự báo.</div>';
                }
            }
            
            // Render tabs
            renderSectorFilterTabs();
            renderMarketTable();
            renderWatchlistTab();
            renderScreenerTab();
            renderBacktestTab();
            renderLogsTab();
            
            // Trigger detailed predict on the default stock to load chart cache
            if (currentSymbol) {
                runPredictForDetails(currentSymbol, false);
            }
        }
    } catch (e) {
        console.error('App init failed:', e);
    } finally {
        hideLoading();
    }
}

// Check if model is loaded on start
async function checkModelStatus() {
    try {
        const response = await fetch('/api/model-status');
        const data = await response.json();
        if (data.loaded) {
            statusDot.className = 'status-dot connected';
            statusText.textContent = `Đã nạp: ${data.current_model.name} (${data.current_model.device})`;
            activeModel = data.current_model.name;
        } else {
            statusDot.className = 'status-dot simulated';
            statusText.textContent = 'Chế độ: Mô phỏng (Sẵn sàng)';
        }
    } catch (e) {
        console.error('Model status fetch failed:', e);
    }
}

// Fetch model types
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
    } catch (e) {
        console.error('Fetch models failed:', e);
    }
}

// Load Model Handler
async function loadModel() {
    const modelKey = modelSelect.value;
    const device = deviceSelect.value;
    showLoading(`Đang nạp mô hình ${modelSelect.options[modelSelect.selectedIndex].text}...`);
    try {
        const response = await fetch('/api/load-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_key: modelKey, device: device })
        });
        const data = await response.json();
        if (data.success) {
            statusDot.className = 'status-dot connected';
            statusText.textContent = `Đã nạp: ${data.model_info.name} (${device})`;
            activeModel = data.model_info.name;
            showToast(`Nạp mô hình thành công! ${data.model_info.name} sẵn sàng chạy suy luận.`, 'success');
        } else {
            showToast('Lỗi nạp mô hình', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Không kết nối được server', 'error');
    } finally {
        hideLoading();
    }
}

// Update Top 1 Hero details
function updateHeroCard(stock) {
    heroStockSymbol.textContent = stock.symbol;
    heroStockExchange.textContent = stock.exchange;
    heroStockName.textContent = stock.name;
    
    heroStockPrice.textContent = formatPrice(stock.current_close) + ' ₫';
    
    const diff = stock.current_close - stock.prev_close;
    const change = (diff / stock.prev_close) * 100;
    heroStockChange.textContent = `${diff >= 0 ? '+' : ''}${formatPrice(diff)} ₫ (${formatPct(change)})`;
    heroStockChange.className = diff >= 0 ? 'price-change text-up' : 'price-change text-down';
    
    heroTargetPrice.textContent = formatPrice(stock.pred_close_5d) + ' ₫';
    
    const returnVal = stock.predicted_return * 100;
    heroTargetReturn.textContent = formatPct(returnVal);
    heroTargetReturn.className = `stat-val price ${returnVal >= 0 ? 'text-up' : 'text-down'}`;
    
    heroVolatility.textContent = (stock.rmse !== null && stock.rmse !== undefined) ? stock.rmse.toFixed(1) + '%' : '--%';
    
    // Trend badge
    heroTrendIndicator.textContent = stock.trend === 'up' ? 'Tăng' : stock.trend === 'down' ? 'Giảm' : 'Đi ngang';
    heroTrendIndicator.className = `trend-badge-lbl ${stock.trend === 'up' ? 'trend-up' : (stock.trend === 'down' ? 'trend-down' : 'trend-sideway')}`;
    
    // Confidence dots
    let dotsHtml = '';
    for (let i = 1; i <= 5; i++) {
        dotsHtml += `<span class="dot ${i <= stock.confidence ? 'active' : ''}"></span>`;
    }
    heroConfidenceDots.innerHTML = dotsHtml;
    
    // Render Hero Area Chart
    renderHeroChart(stock);
}

// Render Sector Filter Tabs
function renderSectorFilterTabs() {
    sectorTabs.innerHTML = '';
    
    SECTOR_LIST.forEach(secName => {
        const count = secName === 'Tất cả' ? allStocks.length : allStocks.filter(s => s.sector === secName).length;
        if (count === 0 && secName !== 'Tất cả') return; // Skip empty sectors
        
        const btn = document.createElement('button');
        btn.className = `sector-tab ${activeSectorFilter === secName ? 'active' : ''}`;
        btn.innerHTML = `${secName} <span class="sector-tab-count">${count}</span>`;
        
        btn.addEventListener('click', () => {
            activeSectorFilter = secName;
            document.querySelectorAll('.sector-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderMarketTable();
        });
        
        sectorTabs.appendChild(btn);
    });
}

// Toggle Trend filters
function toggleTrendFilter(trend) {
    if (activeTrendFilter === trend) {
        activeTrendFilter = null;
        document.querySelectorAll('.tile-btn').forEach(b => b.classList.remove('active'));
    } else {
        activeTrendFilter = trend;
        document.querySelectorAll('.tile-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(`tile-${trend}`).classList.add('active');
    }
    renderMarketTable();
}

// Render Overview Market Table
function renderMarketTable() {
    overviewTableBody.innerHTML = '';
    
    // Filter stocks list
    let filtered = allStocks;
    if (activeSectorFilter !== 'Tất cả') {
        filtered = filtered.filter(s => s.sector === activeSectorFilter);
    }
    if (activeTrendFilter) {
        filtered = filtered.filter(s => s.trend === activeTrendFilter);
    }
    
    // Tile summaries counts
    const upCount = allStocks.filter(s => s.trend === 'up').length;
    const downCount = allStocks.filter(s => s.trend === 'down').length;
    const sideCount = allStocks.filter(s => s.trend === 'sideway').length;
    
    const avg = (arr, selector) => arr.length ? arr.reduce((acc, x) => acc + selector(x), 0) / arr.length : 0;
    const upAvg = avg(allStocks.filter(s => s.trend === 'up'), s => s.predicted_return * 100);
    const downAvg = avg(allStocks.filter(s => s.trend === 'down'), s => s.predicted_return * 100);
    const sideAvg = avg(allStocks.filter(s => s.trend === 'sideway'), s => s.predicted_return * 100);
    
    countsUp.textContent = upCount;
    countsDown.textContent = downCount;
    countsSide.textContent = sideCount;
    
    avgUp.textContent = `Cổ phiếu · TB ${formatPct(upAvg)}`;
    avgDown.textContent = `Cổ phiếu · TB ${formatPct(downAvg)}`;
    avgSide.textContent = `Cổ phiếu · TB ${formatPct(sideAvg)}`;

    // Pagination slice
    const sliced = filtered.slice(0, overviewLimit);
    overviewTableCount.textContent = `Đang hiển thị ${Math.min(overviewLimit, filtered.length)} / ${filtered.length} cổ phiếu`;
    
    if (overviewLimit >= filtered.length) {
        overviewLoadMore.style.display = 'none';
    } else {
        overviewLoadMore.style.display = 'inline-block';
    }

    if (sliced.length === 0) {
        overviewTableBody.innerHTML = '<tr><td colspan="10" class="text-center py-8 text-secondary">Không tìm thấy mã nào phù hợp với bộ lọc.</td></tr>';
        return;
    }
    
    sliced.forEach((s, idx) => {
        const tr = document.createElement('tr');
        
        const diff = s.current_close - s.prev_close;
        const changeVal = (diff / s.prev_close) * 100;
        const changeColorClass = changeVal > 0 ? 'text-up' : (changeVal < 0 ? 'text-down' : 'text-sideway');
        
        // Guard AI fields
        const hasAI = s.predicted_return !== null && s.predicted_return !== undefined;
        const fcVal = hasAI ? s.predicted_return * 100 : 0;
        const fcColorClass = hasAI ? (fcVal > 0 ? 'text-up' : (fcVal < 0 ? 'text-down' : 'text-sideway')) : 'text-secondary';
        
        // Ceiling Floor check
        let ceilFloorBadge = '';
        const ceilPrice = Math.round((s.prev_close * 1.07) / 100) * 100;
        const floorPrice = Math.round((s.prev_close * 0.93) / 100) * 100;
        if (s.current_close >= ceilPrice - 50) {
            ceilFloorBadge = '<span class="cf-badge ceiling ml-2">Trần</span>';
        } else if (s.current_close <= floorPrice + 50) {
            ceilFloorBadge = '<span class="cf-badge floor ml-2">Sàn</span>';
        }

        // Confidence dots
        let dotsHtml = '';
        if (hasAI) {
            for (let i = 1; i <= 5; i++) {
                dotsHtml += `<span class="dot ${i <= s.confidence ? 'active' : ''}" style="width: 5px; height: 5px; margin: 0 1px; display: inline-block; border-radius: 50%; background-color: ${i <= s.confidence ? 'var(--primary)' : 'var(--secondary)'}"></span>`;
            }
        } else {
            dotsHtml = '<span class="text-secondary">--</span>';
        }
        
        // Sparkline cell representation via dynamic SVG drawing
        const sparklineSvg = drawMiniSparklineSvg(s.sparkline_candles);
        
        const trendHtml = hasAI ? `
            <span class="badge-trend ${s.trend}">
                <i data-lucide="${s.trend === 'up' ? 'arrow-up' : (s.trend === 'down' ? 'arrow-down' : 'arrow-right')}" style="width: 10px; height: 10px; display: inline-block;"></i>
                ${s.trend === 'up' ? 'Tăng' : (s.trend === 'down' ? 'Giảm' : 'Ngang')}
            </span>
        ` : '<span class="text-secondary">--</span>';
        
        const riskHtml = hasAI ? `
            <div style="height: 4px; background-color: var(--secondary); border-radius: 2px; overflow: hidden; margin-top: 4px; width: 100px;">
                <div style="height: 100%; width: ${s.risk_score}%; background-color: ${s.risk_score >= 60 ? 'var(--down)' : (s.risk_score >= 40 ? 'var(--warning)' : 'var(--up)')}"></div>
            </div>
            <div class="font-mono text-[9px] text-secondary mt-1">${s.risk_score}/100</div>
        ` : '<span class="text-secondary">--</span>';
        
        const forecastPriceHtml = hasAI ? `
            <div class="font-semibold">${formatPrice(s.pred_close_5d)}</div>
            <div class="text-[10px]">(${formatPct(fcVal)})</div>
        ` : '<div class="text-secondary">--</div>';
        
        tr.innerHTML = `
            <td class="text-center font-mono text-xs text-muted">${idx + 1}</td>
            <td>
                <a href="#" class="details-link font-bold text-foreground font-mono" style="text-decoration: none;">${s.symbol}</a>
                <div class="text-secondary text-[10px]" style="max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${s.name}</div>
            </td>
            <td>
                <span class="exchange-tag text-[9px]">${s.exchange}</span>
                ${ceilFloorBadge}
            </td>
            <td class="text-right font-mono font-semibold ${changeColorClass}">${formatPrice(s.current_close)}</td>
            <td class="text-right font-mono ${changeColorClass}">${formatPct(changeVal)}</td>
            <td class="text-center">${dotsHtml}</td>
            <td>${trendHtml}</td>
            <td>${riskHtml}</td>
            <td class="text-right font-mono ${fcColorClass}">${forecastPriceHtml}</td>
            <td class="text-center">${sparklineSvg}</td>
        `;
        
        // Link triggers details view
        const link = tr.querySelector('.details-link');
        link.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab('details');
            runPredictForDetails(s.symbol, true);
        });
        
        overviewTableBody.appendChild(tr);
    });
    
    lucide.createIcons();
}

// Dynamic Sparkline candle drawer using dynamic SVG strings
function drawMiniSparklineSvg(candles) {
    if (!candles || candles.length === 0) return '--';
    
    const width = 80;
    const height = 30;
    const min = Math.min(...candles.map(c => c.low));
    const max = Math.max(...candles.map(c => c.high));
    const range = max - min || 1;
    
    const slot = width / candles.length;
    const bodyW = Math.max(2, slot * 0.6);
    
    const y = (v) => height - ((v - min) / range) * (height - 4) - 2;
    
    let svgContent = `<svg width="${width}" height="${height}" style="overflow: visible;">`;
    
    candles.forEach((c, i) => {
        const x = i * slot + slot / 2;
        const up = c.close >= c.open;
        const color = up ? 'var(--up)' : 'var(--down)';
        const opacity = c.fcst ? 1 : 0.35;
        const top = y(Math.max(c.open, c.close));
        const bot = y(Math.min(c.open, c.close));
        
        svgContent += `
            <g opacity="${opacity}">
                <line x1="${x}" x2="${x}" y1="${y(c.high)}" y2="${y(c.low)}" stroke="${color}" stroke-width="1" />
                <rect x="${x - bodyW / 2}" y="${top}" width="${bodyW}" height="${Math.max(1, bot - top)}" fill="${color}" />
            </g>
        `;
    });
    
    // vertical divider
    svgContent += `
        <line x1="${3 * slot}" x2="${3 * slot}" y1="0" y2="${height}" stroke="var(--primary)" stroke-dasharray="2,2" stroke-width="0.5" opacity="0.5" />
    `;
    svgContent += `</svg>`;
    return svgContent;
}

// Render Screener Tab
function renderScreenerTab() {
    runScreenerFiltering();
}

function runScreenerFiltering() {
    screenerTableBody.innerHTML = '';
    
    const sector = screenerSectorSelect.value;
    const trendBtn = document.querySelector('#screener-trend-group .btn.active');
    const trend = trendBtn ? trendBtn.getAttribute('data-trend') : 'all';
    const minConf = parseInt(screenerConfSlider.value);
    const maxRisk = parseInt(screenerRiskSlider.value);
    
    let filtered = allStocks.filter(s => {
        if (sector !== 'Tất cả' && s.sector !== sector) return false;
        if (trend !== 'all' && s.trend !== trend) return false;
        if (s.confidence < minConf) return false;
        if (s.risk_score > maxRisk) return false;
        return true;
    });
    
    // Sort screener by expected return descending
    filtered = filtered.sort((a, b) => b.predicted_return - a.predicted_return);
    
    screenerMatchCount.textContent = filtered.length;
    
    if (filtered.length === 0) {
        screenerTableBody.innerHTML = '<tr><td colspan="8" class="text-center py-8 text-secondary">Không tìm thấy mã nào phù hợp với bộ lọc.</td></tr>';
        return;
    }
    
    filtered.forEach(s => {
        const tr = document.createElement('tr');
        
        const diff = s.current_close - s.prev_close;
        const changeVal = (diff / s.prev_close) * 100;
        const changeColorClass = changeVal > 0 ? 'text-up' : (changeVal < 0 ? 'text-down' : 'text-sideway');
        
        const hasAI = s.predicted_return !== null && s.predicted_return !== undefined;
        const fcVal = hasAI ? s.predicted_return * 100 : null;
        const fcColorClass = hasAI ? (fcVal > 0 ? 'text-up' : (fcVal < 0 ? 'text-down' : 'text-sideway')) : 'text-secondary';

        let dotsHtml = '';
        if (hasAI) {
            for (let i = 1; i <= 5; i++) {
                dotsHtml += `<span class="dot ${i <= s.confidence ? 'active' : ''}" style="width: 5px; height: 5px; margin: 0 1px; display: inline-block; border-radius: 50%; background-color: ${i <= s.confidence ? 'var(--primary)' : 'var(--secondary)'}"></span>`;
            }
        } else {
            dotsHtml = '<span class="text-secondary">--</span>';
        }
        
        const trendHtml = hasAI ? `
            <span class="badge-trend ${s.trend}">
                <i data-lucide="${s.trend === 'up' ? 'arrow-up' : (s.trend === 'down' ? 'arrow-down' : 'arrow-right')}" style="width: 10px; height: 10px; display: inline-block;"></i>
                ${s.trend === 'up' ? 'Tăng' : (s.trend === 'down' ? 'Giảm' : 'Ngang')}
            </span>
        ` : '<span class="text-secondary">--</span>';
        
        const riskHtml = hasAI ? `
            <div style="height: 4px; background-color: var(--secondary); border-radius: 2px; overflow: hidden; margin-top: 4px; width: 100px;">
                <div style="height: 100%; width: ${s.risk_score}%; background-color: ${s.risk_score >= 60 ? 'var(--down)' : (s.risk_score >= 40 ? 'var(--warning)' : 'var(--up)')}"></div>
            </div>
            <div class="font-mono text-[9px] text-secondary mt-1">${s.risk_score}/100</div>
        ` : '<span class="text-secondary">--</span>';
        
        tr.innerHTML = `
            <td>
                <a href="#" class="screener-link font-bold text-foreground font-mono" style="text-decoration: none;">${s.symbol}</a>
                <div class="text-secondary text-[10px]" style="max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${s.name}</div>
            </td>
            <td class="text-secondary text-xs">${s.sector}</td>
            <td class="text-right font-mono font-semibold">${formatPrice(s.current_close)}</td>
            <td class="text-right font-mono ${changeColorClass}">${formatPct(changeVal)}</td>
            <td class="text-right font-mono ${fcColorClass}">${formatPct(fcVal)}</td>
            <td>${trendHtml}</td>
            <td class="text-center">${dotsHtml}</td>
            <td>${riskHtml}</td>
        `;
        
        // Trigger details click
        tr.querySelector('.screener-link').addEventListener('click', (e) => {
            e.preventDefault();
            switchTab('details');
            runPredictForDetails(s.symbol, true);
        });
        
        screenerTableBody.appendChild(tr);
    });
    
    lucide.createIcons();
}

// Render Watchlist Tab
function renderWatchlistTab() {
    // Clear watchlist grid content except the form
    const cards = watchlistGrid.querySelectorAll('.watchlist-card');
    cards.forEach(c => c.remove());
    
    const watchedStocks = allStocks.filter(s => watchlist.includes(s.symbol));
    
    // Loop watched stocks and append cards before form
    watchedStocks.forEach(s => {
        const card = document.createElement('a');
        card.href = '#';
        card.className = 'watchlist-card card';
        
        const diff = s.current_close - s.prev_close;
        const changeVal = (diff / s.prev_close) * 100;
        const changeColorClass = changeVal > 0 ? 'text-up' : (changeVal < 0 ? 'text-down' : 'text-sideway');
        
        const fcVal = s.predicted_return * 100;
        const fcColorClass = fcVal > 0 ? 'text-up' : (fcVal < 0 ? 'text-down' : 'text-sideway');
        
        const sparklineSvg = drawMiniSparklineSvg(s.sparkline_candles);
        
        card.innerHTML = `
            <button class="btn-remove-watch" title="Bỏ theo dõi" data-sym="${s.symbol}">&times;</button>
            <div class="card-header-line">
                <div class="card-symbol-line">
                    <h4>${s.symbol}</h4>
                    <span class="exchange-tag text-[9px]">${s.exchange}</span>
                </div>
                <span class="card-price font-semibold">${formatPrice(s.current_close)} ₫</span>
            </div>
            <div class="card-sub-line">
                <span class="${changeColorClass}">${formatPct(changeVal)}</span>
                <span>KL: ${formatVolume(s.volume)}</span>
            </div>
            <div class="card-trend-line">
                <span class="badge-trend ${s.trend} text-[10px]">
                    ${s.trend === 'up' ? 'Tăng' : (s.trend === 'down' ? 'Giảm' : 'Ngang')}
                </span>
                <div class="risk-bar-wrap">
                    <div style="height: 4px; background-color: var(--secondary); border-radius: 2px; overflow: hidden; width: 100%;">
                        <div style="height: 100%; width: ${s.risk_score}%; background-color: ${s.risk_score >= 60 ? 'var(--down)' : (s.risk_score >= 40 ? 'var(--warning)' : 'var(--up)')}"></div>
                    </div>
                </div>
            </div>
            <div class="card-footer-line">
                <div class="text-secondary text-[10px]">
                    Mục tiêu: <span class="font-mono text-foreground font-semibold">${formatPrice(s.pred_close_5d)}</span> 
                    <span class="${fcColorClass}">(${formatPct(fcVal)})</span>
                </div>
                <div class="card-sparkline">${sparklineSvg}</div>
            </div>
        `;
        
        // Remove button click
        const removeBtn = card.querySelector('.btn-remove-watch');
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            const symbolToRemove = removeBtn.getAttribute('data-sym');
            watchlist = watchlist.filter(x => x !== symbolToRemove);
            localStorage.setItem('watchlist', JSON.stringify(watchlist));
            renderWatchlistTab();
        });
        
        // Click navigates to details
        card.addEventListener('click', (e) => {
            if (e.target !== removeBtn) {
                switchTab('details');
                runPredictForDetails(s.symbol, true);
            }
        });
        
        watchlistGrid.insertBefore(card, watchlistAddForm);
    });

    // Calculate distributions for right sidebar panels
    const totalCount = watchedStocks.length;
    
    // Panel 1: Trend distribution
    watchlistTrendBars.innerHTML = '';
    if (totalCount === 0) {
        watchlistTrendBars.innerHTML = '<div class="text-center py-4 text-secondary">Chưa theo dõi mã nào.</div>';
    } else {
        const upW = watchedStocks.filter(s => s.trend === 'up').length;
        const downW = watchedStocks.filter(s => s.trend === 'down').length;
        const sideW = watchedStocks.filter(s => s.trend === 'sideway').length;
        
        const trendDist = [
            { name: 'Tăng', value: upW, color: 'bg-up' },
            { name: 'Giảm', value: downW, color: 'bg-down' },
            { name: 'Đi ngang', value: sideW, color: 'bg-warning' }
        ];
        
        trendDist.forEach(d => {
            const pct = totalCount > 0 ? (d.value / totalCount) * 100 : 0;
            const div = document.createElement('div');
            div.className = 'prob-bar-item';
            div.innerHTML = `
                <div class="prob-bar-label text-xs">
                    <span class="text-secondary">${d.name}</span>
                    <span class="font-mono font-semibold">${d.value} mã (${pct.toFixed(0)}%)</span>
                </div>
                <div class="prob-bar-track">
                    <div class="prob-bar-fill ${d.color}" style="width: ${pct}%"></div>
                </div>
            `;
            watchlistTrendBars.appendChild(div);
        });
    }

    // Panel 2: Risk distribution
    watchlistRiskBars.innerHTML = '';
    if (totalCount === 0) {
        watchlistRiskBars.innerHTML = '<div class="text-center py-4 text-secondary">Chưa theo dõi mã nào.</div>';
    } else {
        const highRiskCount = watchedStocks.filter(s => s.risk_score >= 60).length;
        const midRiskCount = watchedStocks.filter(s => s.risk_score >= 40 && s.risk_score < 60).length;
        const lowRiskCount = watchedStocks.filter(s => s.risk_score < 40).length;
        
        const riskDist = [
            { label: 'Rủi ro cao', value: highRiskCount, color: 'bg-down' },
            { label: 'Rung lắc TB', value: midRiskCount, color: 'bg-warning' },
            { label: 'Bình ổn thấp', value: lowRiskCount, color: 'bg-up' }
        ];
        
        riskDist.forEach(d => {
            const pct = totalCount > 0 ? (d.value / totalCount) * 100 : 0;
            const div = document.createElement('div');
            div.className = 'prob-bar-item';
            div.innerHTML = `
                <div class="prob-bar-label text-xs">
                    <span class="text-secondary">${d.label}</span>
                    <span class="font-mono font-semibold">${d.value} mã (${pct.toFixed(0)}%)</span>
                </div>
                <div class="prob-bar-track">
                    <div class="prob-bar-fill ${d.color}" style="width: ${pct}%"></div>
                </div>
            `;
            watchlistRiskBars.appendChild(div);
        });
    }

    // Panel 3: Active risk alerts
    watchlistAlertsList.innerHTML = '';
    const activeAlerts = watchedStocks.filter(s => s.risk_score >= 70);
    if (activeAlerts.length === 0) {
        watchlistAlertsList.innerHTML = '<div class="text-secondary text-xs">Không có cảnh báo rủi ro cao nào kích hoạt.</div>';
    } else {
        activeAlerts.forEach(s => {
            const div = document.createElement('div');
            div.className = 'alert-item';
            div.innerHTML = `
                <i data-lucide="alert-triangle" class="text-down"></i>
                <div>
                    <div class="font-bold font-mono">${s.symbol}</div>
                    <div class="text-secondary text-[11px]">Rủi ro tăng vọt (${s.risk_score}/100), dự báo có xu hướng biến động ${formatPct(s.predicted_return * 100)} trong 5 phiên tới.</div>
                </div>
            `;
            watchlistAlertsList.appendChild(div);
        });
        lucide.createIcons();
    }
}

// Render Backtest tab
function renderBacktestTab() {
    // 1. Cập nhật các KPI thật từ reportsData
    if (reportsData && reportsData.finetuned) {
        const ft = reportsData.finetuned;
        const bs = reportsData.baseline;
        
        if (ft.da) {
            const testDaVal = ft.da.test;
            document.getElementById('kpi-da-val').textContent = testDaVal.toFixed(1) + '%';
            document.getElementById('kpi-da-sub').textContent = `DA (Test) · Baseline ${bs && bs.da ? bs.da.test.toFixed(1) : '52.8'}%`;
            const daStatus = document.getElementById('kpi-da-status');
            if (testDaVal >= 52.0) {
                daStatus.textContent = '✓ Đạt';
                daStatus.className = 'kpi-status text-up mt-1';
            } else {
                daStatus.textContent = '⚠ Cận biên';
                daStatus.className = 'kpi-status text-warning mt-1';
            }
        }
        
        if (ft.rank_ic) {
            const testRankIC = ft.rank_ic.test;
            document.getElementById('kpi-rankic-val').textContent = testRankIC.toFixed(3);
            document.getElementById('kpi-rankic-sub').textContent = `RankIC (Test) · Baseline ${bs && bs.rank_ic ? bs.rank_ic.test.toFixed(3) : '0.017'}`;
        }
        
        if (ft.ann_return_long) {
            const testReturn = ft.ann_return_long.test;
            document.getElementById('kpi-return-val').textContent = (testReturn >= 0 ? '+' : '') + testReturn.toFixed(1) + '%';
            document.getElementById('kpi-return-sub').textContent = `Ann Return vs Bench ${ft.ann_return_bench ? ft.ann_return_bench.test.toFixed(1) : '26.0'}%`;
        }
        
        if (ft.win_rate_long) {
            const testWinRate = ft.win_rate_long.test;
            document.getElementById('kpi-winrate-val').textContent = testWinRate.toFixed(1) + '%';
            document.getElementById('kpi-winrate-sub').textContent = `Win Rate (Test)`;
            const wrStatus = document.getElementById('kpi-winrate-status');
            if (testWinRate >= 50.0) {
                wrStatus.textContent = '✓ Tốt';
                wrStatus.className = 'kpi-status text-up mt-1';
            } else {
                wrStatus.textContent = '⚠ Yếu';
                wrStatus.className = 'kpi-status text-warning mt-1';
            }
        }
    }
    
    backtestTableBody.innerHTML = '';
    
    // Populate Fold table (top 20)
    const top20 = allStocks.slice(0, 20);
    top20.forEach(s => {
        const tr = document.createElement('tr');
        
        const sDa = s.da !== null && s.da !== undefined ? s.da.toFixed(1) + '%' : '--%';
        const sMae = s.mae !== null && s.mae !== undefined ? s.mae.toFixed(1) + '%' : '--%';
        const sRmse = s.rmse !== null && s.rmse !== undefined ? s.rmse.toFixed(1) + '%' : '--%';
        const sCov = s.coverage !== null && s.coverage !== undefined ? s.coverage.toFixed(1) + '%' : '--%';
        
        const daColorClass = s.da && s.da > 55 ? 'text-up' : (s.da && s.da > 52 ? 'text-warning' : 'text-secondary');
        const statusText = s.da && s.da > 55 ? '✓ Tốt' : (s.da && s.da > 52 ? '⚠ Cận hạn' : '--');
        const statusColorClass = s.da && s.da > 55 ? 'text-up' : (s.da && s.da > 52 ? 'text-warning' : 'text-secondary');
        const barColorClass = s.da && s.da > 55 ? 'bg-up' : (s.da && s.da > 52 ? 'bg-warning' : 'bg-secondary');
        const barWidth = s.da ? Math.min(100, (s.da - 45) * 6.7) : 0;
        
        tr.innerHTML = `
            <td class="px-3 py-2 font-bold text-foreground font-mono">${s.symbol}</td>
            <td class="px-3 py-2">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="width: 45px; display: inline-block;" class="${daColorClass}">${sDa}</span>
                    <div style="flex: 1; height: 6px; border-radius: 3px; background-color: var(--secondary); overflow: hidden; max-width: 150px;">
                        <div class="${barColorClass}" style="height: 100%; width: ${barWidth}%"></div>
                    </div>
                </div>
            </td>
            <td class="px-3 py-2 text-right">${sMae}</td>
            <td class="px-3 py-2 text-right">${sRmse}</td>
            <td class="px-3 py-2 text-right">${sCov}</td>
            <td class="px-3 py-2 ${statusColorClass} font-semibold font-sans">${statusText}</td>
        `;
        backtestTableBody.appendChild(tr);
    });

    // Populate Daily logs Cards
    backtestDailyCards.innerHTML = '';
    
    if (reportsData && reportsData.daily_logs && reportsData.daily_logs.length > 0) {
        const displayLogs = reportsData.daily_logs.slice(0, 7);
        displayLogs.forEach(d => {
            const card = document.createElement('div');
            const daVal = d.da * 100;
            const isGood = daVal >= 55;
            const isBad = daVal < 52;
            const typeClass = isGood ? 'da-good' : (isBad ? 'da-bad' : 'da-ok');
            
            card.className = `daily-log-card ${typeClass}`;
            card.innerHTML = `
                <div class="log-date" style="font-size: 11px;">${formatVnDateLong(d.date)}</div>
                <div class="mt-2 text-secondary" style="font-size: 11px;">
                    RankIC: <span class="font-mono text-foreground font-semibold">${d.rank_ic.toFixed(3)}</span>
                </div>
                <div class="text-secondary mt-1" style="font-size: 10px; max-height: 36px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
                    Mã Long: <span class="font-mono text-foreground">${d.long_symbols}</span>
                </div>
                <div class="log-row-stat" style="margin-top: 6px;">
                    DA Ngày: <span class="font-bold text-foreground font-mono">${daVal.toFixed(1)}%</span>
                </div>
            `;
            backtestDailyCards.appendChild(card);
        });
    } else {
        DAILY_LOG_DATA.forEach(d => {
            const card = document.createElement('div');
            const isGood = d.da >= 60;
            const isBad = d.da < 52;
            const typeClass = isGood ? 'da-good' : (isBad ? 'da-bad' : 'da-ok');
            
            card.className = `daily-log-card ${typeClass}`;
            card.innerHTML = `
                <div class="log-date">${d.date}</div>
                <div class="mt-2 text-secondary">
                    Dự báo: <span class="font-mono text-foreground font-semibold">${d.predicted}</span>
                </div>
                <div class="text-secondary mt-1">
                    Thực tế: <span class="font-mono text-foreground font-semibold">${d.actual}</span> 
                    <span class="${d.predicted === d.actual ? 'text-up' : 'text-down'}">${d.predicted === d.actual ? '✓' : '✗'}</span>
                </div>
                <div class="log-row-stat">
                    DA: <span class="font-bold text-foreground font-mono">${d.da}%</span> (${d.correct}/${d.total})
                </div>
            `;
            backtestDailyCards.appendChild(card);
        });
    }

    // Render Backtest Line chart
    renderBacktestFoldChart();
}

// Render Logs tab
function renderLogsTab() {
    logsTableBody.innerHTML = '';
    
    if (reportsData && reportsData.daily_logs && reportsData.daily_logs.length > 0) {
        reportsData.daily_logs.forEach(d => {
            const tr = document.createElement('tr');
            const daVal = d.da * 100;
            const colorClass = daVal >= 55 ? 'text-up' : (daVal >= 52 ? 'text-warning' : 'text-down');
            
            tr.innerHTML = `
                <td class="px-4 py-3 text-sm">${formatVnDateLong(d.date)}</td>
                <td class="px-4 py-3 font-mono" style="font-size: 11px; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${d.long_symbols}</td>
                <td class="px-4 py-3 font-mono text-right">${d.rank_ic.toFixed(3)}</td>
                <td class="px-4 py-3 text-right font-semibold font-mono ${colorClass}">${daVal.toFixed(1)}%</td>
                <td class="px-4 py-3 text-right font-mono text-secondary">--/50</td>
            `;
            logsTableBody.appendChild(tr);
        });
    } else {
        DAILY_LOG_DATA.forEach(d => {
            const tr = document.createElement('tr');
            const correct = d.predicted === d.actual;
            const colorClass = d.da >= 60 ? 'text-up' : (d.da >= 52 ? 'text-warning' : 'text-down');
            
            tr.innerHTML = `
                <td class="px-4 py-3 text-sm">${d.date}</td>
                <td class="px-4 py-3 font-mono font-semibold">${d.predicted}</td>
                <td class="px-4 py-3 font-mono">
                    <span class="${correct ? 'text-up' : 'text-down'}">${d.actual}</span> 
                    <span class="${correct ? 'text-up' : 'text-down'}">${correct ? '✓' : '✗'}</span>
                </td>
                <td class="px-4 py-3 text-right font-semibold font-mono ${colorClass}">${d.da}%</td>
                <td class="px-4 py-3 text-right font-mono text-secondary">${d.correct}/${d.total}</td>
            `;
            logsTableBody.appendChild(tr);
        });
    }
}

// Call API predict details for specific stock
async function runPredictForDetails(symbol, updateDetailsUI = true) {
    if (!symbol) return;
    
    if (updateDetailsUI) {
        showLoading(`Đang phân tích dự báo mã ${symbol}...`);
    }
    
    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_path: `./data/${symbol}.csv`,
                lookback: 126,
                pred_len: 5,
                temperature: parseFloat(tempInput.value),
                top_p: parseFloat(topPInput.value),
                sample_count: parseInt(samplesInput.value),
                start_date: startDateInput.value || null
            })
        });
        
        if (response.status === 409) {
            if (updateDetailsUI) {
                showToast(`Yêu cầu nạp mô hình: Vui lòng vào tab Cài đặt, chọn thiết bị và bấm Nạp mô hình trước khi thực hiện dự báo.`, 'warning');
            }
            return;
        }
        
        const data = await response.json();
        if (data.success) {
            currentSymbol = data.symbol;
            
            // Sync settings dropdown and date
            stockSelect.value = currentSymbol;
            
            if (updateDetailsUI) {
                renderDetailsUI(data);
            }
        } else {
            showToast(`Dự báo ${symbol} thất bại: ${data.detail || data.error}`, 'error');
        }
    } catch (e) {
        console.error(e);
        if (updateDetailsUI) {
            showToast('Lỗi truy vấn dự báo từ server. Vui lòng kiểm tra xem mô hình đã được nạp hay chưa.', 'error');
        }
    } finally {
        if (updateDetailsUI) {
            hideLoading();
        }
    }
}

// Render detailed analysis UI panels
function renderDetailsUI(data) {
    // 1. Update Breadcrumbs and header
    detailsBreadcrumbSymbol.textContent = `${data.symbol} — ${data.name}`;
    if (currentTab === 'details') {
        currentTabTitle.textContent = `Chi tiết & Dự báo AI — ${data.symbol}`;
    }
    detailsStockLogoLetters.textContent = data.symbol.slice(0, 2);
    detailsStockSymbol.textContent = data.symbol;
    detailsStockExchange.textContent = data.exchange;
    detailsStockName.textContent = data.name;
    
    const lastHist = data.raw_candles[data.raw_candles.length - data.prediction_results.length - 1];
    const prevHist = data.raw_candles[data.raw_candles.length - data.prediction_results.length - 2];
    
    detailsStockPrice.textContent = formatPrice(lastHist.close);
    
    const diff = lastHist.close - (prevHist ? prevHist.close : lastHist.open);
    const changePct = (diff / (prevHist ? prevHist.close : lastHist.open)) * 100;
    detailsStockChange.textContent = `${diff >= 0 ? '+' : ''}${formatPrice(diff)} ₫ (${formatPct(changePct)})`;
    detailsStockChange.className = `change-line font-mono font-semibold ${diff >= 0 ? 'text-up' : 'text-down'}`;

    // Ceiling floor labels
    const refP = prevHist ? prevHist.close : lastHist.open;
    const ceilP = Math.round((refP * 1.07) / 100) * 100;
    const floorP = Math.round((refP * 0.93) / 100) * 100;
    
    detailsRefPrice.textContent = formatPrice(refP);
    detailsCeilPrice.textContent = formatPrice(ceilP);
    detailsFloorPrice.textContent = formatPrice(floorP);
    
    detailsCeilingFloorBadgeContainer.innerHTML = '';
    if (lastHist.close >= ceilP - 50) {
        detailsCeilingFloorBadgeContainer.innerHTML = '<span class="cf-badge ceiling">Trần</span>';
    } else if (lastHist.close <= floorP + 50) {
        detailsCeilingFloorBadgeContainer.innerHTML = '<span class="cf-badge floor">Sàn</span>';
    }

    // Trend badge large
    const returnVal = data.trend.predicted_return * 100;
    const trendClass = data.trend.trend_class.toLowerCase();
    detailsTrendBadgeContainer.innerHTML = `
        <span class="badge-trend ${trendClass}" style="height: 28px; padding: 0 12px; font-size: 12px;">
            <i data-lucide="${trendClass === 'up' ? 'arrow-up' : (trendClass === 'down' ? 'arrow-down' : 'arrow-right')}" style="width: 14px; height: 14px; display: inline-block;"></i>
            ${trendClass === 'up' ? 'Tăng' : (trendClass === 'down' ? 'Giảm' : 'Đi ngang')}
        </span>
    `;

    // Confidence Level
    const f5 = data.prediction_results[data.prediction_results.length - 1];
    const widthVal = data.risk_metrics.confidence_width;
    const bandWidthPct = (widthVal / f5.close) * 100;
    let confidenceVal = 3;
    if (bandWidthPct > 15) confidenceVal = 1;
    else if (bandWidthPct > 10) confidenceVal = 2;
    else if (bandWidthPct > 7) confidenceVal = 3;
    else if (bandWidthPct > 5) confidenceVal = 4;
    else confidenceVal = 5;

    let dotsHtml = '';
    for (let i = 1; i <= 5; i++) {
        dotsHtml += `<span class="dot ${i <= confidenceVal ? 'active' : ''}"></span>`;
    }
    detailsConfidenceDots.innerHTML = dotsHtml;
    detailsConfidenceText.textContent = confidenceVal >= 4 ? 'cao' : (confidenceVal >= 3 ? 'trung bình' : 'thấp');

    // Vol and Amt Info display text
    detailsChartSymbol.textContent = data.symbol;
    updateTradingViewInfoText(lastHist, prevHist ? prevHist.close : lastHist.open);

    // 2. Render Risk side panel values
    const score = Math.min(100, Math.max(0, Math.round(bandWidthPct * 4 + Math.abs(returnVal) * 4)));
    detailsRiskScore.textContent = `${score}/100`;
    
    // Risk status bar
    let riskLvlLabel = 'Trung bình';
    let riskColorClass = 'bg-warning';
    if (score <= 20) { riskLvlLabel = 'Rất thấp'; riskColorClass = 'bg-up'; }
    else if (score <= 40) { riskLvlLabel = 'Thấp'; riskColorClass = 'bg-success'; }
    else if (score <= 60) { riskLvlLabel = 'Trung bình'; riskColorClass = 'bg-warning'; }
    else if (score <= 80) { riskLvlLabel = 'Cao'; riskColorClass = 'bg-down'; }
    else { riskLvlLabel = 'Rất cao'; riskColorClass = 'bg-error'; }
    
    detailsRiskGaugeContainer.innerHTML = `
        <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px;">
            <span class="text-secondary">Rủi ro:</span>
            <span class="font-bold text-foreground">${riskLvlLabel} (${score}%)</span>
        </div>
        <div style="height:8px; background-color:var(--secondary); border-radius:4px; overflow:hidden; position:relative; width:100%;">
            <div class="${riskColorClass}" style="height:100%; width:${score}%; transition:width var(--transition-normal);"></div>
        </div>
    `;

    detailsF5Close.textContent = formatPrice(f5.close) + ' ₫';
    detailsF5Pct.textContent = `${returnVal >= 0 ? '+' : ''}${returnVal.toFixed(2)}% so với hôm nay`;
    detailsF5Pct.className = `change-pct font-mono text-xs ${returnVal >= 0 ? 'text-up' : 'text-down'}`;

    // Confidence bounds slider positions
    const var5 = data.risk_metrics.var_5pct;
    const var95 = f5.close + (f5.close - var5); // Symmetric mock upper bound for VaR visual representation
    const range = var95 - var5;
    const meanPos = ((f5.close - var5) / range) * 100;
    
    detailsGradientPointer.style.left = `${meanPos}%`;
    detailsGradientLow.textContent = formatPrice(var5);
    detailsGradientHigh.textContent = formatPrice(var95);
    detailsGradientSpread.textContent = `Độ rộng: ${formatPrice(range)} ₫ (${(range / f5.close * 100).toFixed(1)}%)`;

    // Probability breakdown
    // Biased by return direction
    let pUp = 0.33 + (data.trend.predicted_return * 2.5);
    let pDown = 0.33 - (data.trend.predicted_return * 2.0);
    pUp = Math.max(0.05, Math.min(0.85, pUp));
    pDown = Math.max(0.05, Math.min(0.85, pDown));
    let pSide = 1.0 - pUp - pDown;
    
    detailsProbUpVal.textContent = (pUp * 100).toFixed(0) + '%';
    detailsProbSideVal.textContent = (pSide * 100).toFixed(0) + '%';
    detailsProbDownVal.textContent = (pDown * 100).toFixed(0) + '%';
    
    detailsProbUpBar.style.width = (pUp * 100) + '%';
    detailsProbSideBar.style.width = (pSide * 100) + '%';
    detailsProbDownBar.style.width = (pDown * 100) + '%';

    // T+2 calendar calculation
    const today = new Date();
    const t2 = new Date(today);
    t2.setDate(today.getDate() + 3); // roughly T+2 settlement days
    while (t2.getDay() === 0 || t2.getDay() === 6) t2.setDate(t2.getDate() + 1);
    detailsT2Date.textContent = `Quy tắc T+2: mua hôm nay nhận hàng ngày ${String(t2.getDate()).padStart(2, '0')}/${String(t2.getMonth() + 1).padStart(2, '0')}.`;

    // 3. Render Detailed Recharts-like TradingView Candlestick Chart
    renderMainForecastChart(data);

    // 4. Fill Forecast Table Tab
    detailsForecastTableBody.innerHTML = '';
    data.prediction_results.forEach((c, i) => {
        const tr = document.createElement('tr');
        const prevClosePrice = i === 0 ? lastHist.close : data.prediction_results[i-1].close;
        const changeValF = ((c.close - prevClosePrice) / prevClosePrice) * 100;
        const colorClassF = changeValF > 0 ? 'text-up' : 'text-down';
        const opacity = 1.0 - i * 0.08;
        
        tr.className = 'border-b border-border/50';
        tr.style.background = `rgba(56, 139, 253, ${i * 0.025})`;
        tr.innerHTML = `
            <td class="py-2 pr-3 font-sans text-foreground" style="opacity: ${opacity}">${formatVnDate(c.timestamp)}</td>
            <td class="text-right" style="opacity: ${opacity}">${formatPrice(c.open)}</td>
            <td class="text-right text-up" style="opacity: ${opacity}">${formatPrice(c.high)}</td>
            <td class="text-right text-down" style="opacity: ${opacity}">${formatPrice(c.low)}</td>
            <td class="text-right font-semibold text-foreground" style="opacity: ${opacity}">${formatPrice(c.close)}</td>
            <td class="text-right text-secondary" style="opacity: ${opacity}">${(c.volume / 1000000).toFixed(1)}M</td>
            <td class="text-right ${colorClassF}" style="opacity: ${opacity}">${formatPct(changeValF)}</td>
        `;
        detailsForecastTableBody.appendChild(tr);
    });

    // 5. Fill History Table Tab (last 20 sessions)
    detailsHistoryTableBody.innerHTML = '';
    const historyCandlesOnly = data.raw_candles.slice(0, data.raw_candles.length - data.prediction_results.length).reverse();
    const last20 = historyCandlesOnly.slice(0, 20);
    last20.forEach((c, i) => {
        const tr = document.createElement('tr');
        const prevCl = last20[i + 1]?.close ?? c.open;
        const changeValH = ((c.close - prevCl) / prevCl) * 100;
        const colorClassH = changeValH > 0 ? 'text-up' : (changeValH < 0 ? 'text-down' : 'text-sideway');
        
        tr.innerHTML = `
            <td class="py-2 text-foreground font-sans">${formatVnDate(c.timestamp)}</td>
            <td class="text-right">${formatPrice(c.open)}</td>
            <td class="text-right text-up">${formatPrice(c.high)}</td>
            <td class="text-right text-down">${formatPrice(c.low)}</td>
            <td class="text-right font-semibold">${formatPrice(c.close)}</td>
            <td class="text-right ${colorClassH}">${formatPct(changeValH)}</td>
            <td class="text-right text-secondary">${formatVolume(c.volume)}</td>
        `;
        detailsHistoryTableBody.appendChild(tr);
    });

    // 6. Fill XAI Panel tokens
    xaiHeaderTitle.textContent = returnVal > 0 ? 'Tại sao mô hình dự báo TĂNG?' : (returnVal < 0 ? 'Tại sao mô hình dự báo GIẢM?' : 'Tại sao mô hình dự báo ĐI NGANG?');
    
    detailsXaiPatterns.innerHTML = '';
    const topXai = data.xai_data.slice(0, 3);
    const maxFreq = Math.max(...topXai.map(x => x.frequency));
    
    const descriptions = [
        "Tích lũy vùng đáy 3 phiên — khối lượng tăng dần",
        "Nến doji + đảo chiều sáng (bullish reversal)",
        "Breakout vùng kháng cự ngắn hạn",
        "Phân phối đỉnh ngắn hạn — áp lực bán chốt lời",
        "Hỗ trợ động MA20 giữ vững lực cầu"
    ];
    
    topXai.forEach((x, idx) => {
        const pct = maxFreq > 0 ? (x.frequency / maxFreq) * 100 : 0;
        const desc = descriptions[(x.token + idx) % descriptions.length];
        
        const row = document.createElement('div');
        row.style.marginBottom = '12px';
        row.innerHTML = `
            <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px;">
                <span class="font-mono text-foreground font-bold">Token S1 #${x.token}</span>
                <span class="text-secondary">${x.frequency} occurrences (${pct.toFixed(0)}%)</span>
            </div>
            <div style="height:8px; background-color:var(--background); border-radius:4px; overflow:hidden;">
                <div style="height:100%; width:${pct}%; background-color:var(--primary); border-radius:4px;"></div>
            </div>
            <div class="text-secondary text-[11px] mt-1">${desc}</div>
        `;
        detailsXaiPatterns.appendChild(row);
    });

    // Timeline cards (10 days blocks)
    detailsXaiTimeline.innerHTML = '';
    const timelineSeeds = [1, 0, 1, 1, 0, 1, 0, 1, 1, 1];
    timelineSeeds.forEach((v, i) => {
        const cell = document.createElement('div');
        cell.className = `timeline-cell ${v ? 'active' : 'inactive'}`;
        cell.title = `Phiên -${10 - i}: ${v ? 'Có xuất hiện pattern' : 'Không có'}`;
        detailsXaiTimeline.appendChild(cell);
    });
    
    lucide.createIcons();
}

// Update TradingView OHLC info text
function updateTradingViewInfoText(candle, prevClose = null) {
    detailsTvOpen.textContent = formatPrice(candle.open);
    detailsTvHigh.textContent = formatPrice(candle.high);
    detailsTvLow.textContent = formatPrice(candle.low);
    detailsTvClose.textContent = formatPrice(candle.close);
    
    const ref = prevClose !== null ? prevClose : candle.open;
    const diff = candle.close - ref;
    const pct = (diff / ref) * 100;
    
    detailsTvChange.textContent = `${diff >= 0 ? '+' : ''}${formatPrice(diff)} ₫ (${formatPct(pct)})`;
    detailsTvChange.className = `tv-change-val font-mono font-semibold ${diff >= 0 ? 'text-up' : 'text-down'}`;
    
    detailsTvVolume.textContent = formatVolume(candle.volume);
    detailsTvAmount.textContent = formatAmount(candle.amount) + ' ₫';
}

// Draw the detailed Lightweight Candlestick + stochastic chart
function renderMainForecastChart(data) {
    const container = document.getElementById('details-forecast-chart');
    container.innerHTML = ''; // Reset
    
    const colors = getThemeColors();
    
    // Create chart options
    const chartOptions = {
        width: container.clientWidth || 800,
        height: 430,
        layout: {
            background: { type: 'solid', color: colors.background },
            textColor: colors.text,
            fontFamily: 'Inter',
        },
        grid: {
            horzLines: { color: colors.grid },
            vertLines: { color: colors.grid }
        },
        rightPriceScale: {
            borderColor: colors.grid,
            autoScale: true,
            scaleMargins: {
                top: 0.1,
                bottom: 0.1,
            },
        },
        timeScale: {
            borderColor: colors.grid,
            timeVisible: true,
            rightOffset: 20, // Leave blank space on the right for professional look
            barSpacing: 8,   // Larger candlestick spacing for readability
            fixLeftEdge: true,
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        }
    };
    
    detailsChart = LightweightCharts.createChart(container, chartOptions);
    
    // 1. Candlestick series
    detailsCandleSeries = detailsChart.addCandlestickSeries({
        upColor: colors.candleUp,
        downColor: colors.candleDown,
        borderVisible: true,
        borderUpColor: colors.candleUp,
        borderDownColor: colors.candleDown,
        wickVisible: true,
        wickUpColor: colors.candleUp,
        wickDownColor: colors.candleDown,
    });
    
    const totalCandles = data.raw_candles;
    const predLen = data.prediction_results.length;
    const histLen = totalCandles.length - predLen;
    
    const histData = totalCandles.slice(0, histLen).map(c => ({
        time: c.timestamp.split('T')[0],
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close
    }));
    
    detailsCandleSeries.setData(histData);
    
    // 2. Overlay actual comparison candles if they exist
    if (data.has_comparison && data.actual_data.length > 0) {
        const actualSeries = detailsChart.addCandlestickSeries({
            upColor: 'rgba(8, 153, 129, 0.35)',
            downColor: 'rgba(242, 54, 69, 0.35)',
            borderVisible: true,
            borderUpColor: 'rgba(8, 153, 129, 0.35)',
            borderDownColor: 'rgba(242, 54, 69, 0.35)',
            wickVisible: true,
            wickUpColor: 'rgba(8, 153, 129, 0.35)',
            wickDownColor: 'rgba(242, 54, 69, 0.35)',
            lastValueVisible: false, // Hide duplicate last price axis label
        });
        
        const actData = data.actual_data.map(c => ({
            time: c.timestamp.split('T')[0],
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close
        }));
        actualSeries.setData(actData);
    }
    
    const histLastCandle = totalCandles[histLen - 1];
    const predDates = totalCandles.slice(histLen).map(c => c.timestamp.split('T')[0]);
    
    // 3. Draw Stochastic Paths as thin fans
    detailsStochasticSeriesList = [];
    if (data.stochastic_paths && data.stochastic_paths.length > 0) {
        data.stochastic_paths.forEach(path => {
            const pathSeries = detailsChart.addLineSeries({
                color: colors.stochastic,
                lineWidth: 1,
                priceLineVisible: false,
                crosshairMarkerVisible: false,
                lastValueVisible: false, // Prevent scale cluttering
            });
            
            const pathData = [
                { time: histLastCandle.timestamp.split('T')[0], value: histLastCandle.close }
            ];
            for (let i = 0; i < predLen; i++) {
                pathData.push({
                    time: predDates[i],
                    value: path[i][3] // index 3 is close
                });
            }
            pathSeries.setData(pathData);
            detailsStochasticSeriesList.push(pathSeries);
        });
    }

    // 4. Draw Mean prediction line (dashed thicker blue)
    detailsMeanSeries = detailsChart.addLineSeries({
        color: colors.meanPath,
        lineWidth: 3.5,
        lineStyle: LightweightCharts.LineStyle.Dashed,
        priceLineVisible: false,
        lastValueVisible: false, // Prevent scale cluttering
    });
    
    const meanData = [
        { time: histLastCandle.timestamp.split('T')[0], value: histLastCandle.close }
    ];
    for (let i = 0; i < predLen; i++) {
        meanData.push({
            time: predDates[i],
            value: data.prediction_results[i].close
        });
    }
    detailsMeanSeries.setData(meanData);

    // 5. Draw VaR limits lines
    const var5Value = data.risk_metrics.var_5pct;
    const f5 = data.prediction_results[predLen - 1];
    const var95Value = f5.close + (f5.close - var5Value); // Symmetric mock
    
    detailsVar5Series = detailsChart.addLineSeries({
        color: colors.var5,
        lineWidth: 2,
        lineStyle: LightweightCharts.LineStyle.Dotted,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
        lastValueVisible: false, // Prevent scale cluttering
    });
    
    const var5Data = [
        { time: histLastCandle.timestamp.split('T')[0], value: histLastCandle.close },
        { time: predDates[predLen - 1], value: var5Value }
    ];
    detailsVar5Series.setData(var5Data);
    
    detailsVar95Series = detailsChart.addLineSeries({
        color: colors.var95,
        lineWidth: 2,
        lineStyle: LightweightCharts.LineStyle.Dotted,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
        lastValueVisible: false, // Prevent scale cluttering
    });
    
    const var95Data = [
        { time: histLastCandle.timestamp.split('T')[0], value: histLastCandle.close },
        { time: predDates[predLen - 1], value: var95Value }
    ];
    detailsVar95Series.setData(var95Data);

    // 6. Draw Ceiling and Floor reference lines
    const ceilP = Math.round((histLastCandle.close * 1.07) / 100) * 100;
    const floorP = Math.round((histLastCandle.close * 0.93) / 100) * 100;
    
    detailsCeilSeries = detailsChart.addLineSeries({
        color: colors.ceiling,
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.SparseDashed,
        priceLineVisible: false,
        title: 'Trần',
        lastValueVisible: false, // Prevent scale cluttering
    });
    detailsCeilSeries.setData([
        { time: histData[0].time, value: ceilP },
        { time: predDates[predLen - 1], value: ceilP }
    ]);

    detailsFloorSeries = detailsChart.addLineSeries({
        color: colors.floor,
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.SparseDashed,
        priceLineVisible: false,
        title: 'Sàn',
        lastValueVisible: false, // Prevent scale cluttering
    });
    detailsFloorSeries.setData([
        { time: histData[0].time, value: floorP },
        { time: predDates[predLen - 1], value: floorP }
    ]);
    
    // Fit content first to layout, then apply offset for future timeline spacing
    detailsChart.timeScale().fitContent();
    detailsChart.timeScale().applyOptions({
        rightOffset: 20, // Pushes the forecast to center/center-left, keeping future area empty
        barSpacing: 8,   // Professional bar spacing
    });
    
    // Crosshair move handler to update OHLC overlay info line
    detailsChart.subscribeCrosshairMove((param) => {
        if (!param || !param.time || param.point === undefined) {
            // Restore latest history candle OHLC when not hovering
            updateTradingViewInfoText(histLastCandle, histLen > 1 ? totalCandles[histLen - 2].close : histLastCandle.open);
            return;
        }
        
        let timeStr = '';
        if (typeof param.time === 'string') {
            timeStr = param.time;
        } else if (typeof param.time === 'number') {
            const d = new Date(param.time * 1000);
            const y = d.getUTCFullYear();
            const m = String(d.getUTCMonth() + 1).padStart(2, '0');
            const day = String(d.getUTCDate()).padStart(2, '0');
            timeStr = `${y}-${m}-${day}`;
        } else if (param.time && typeof param.time === 'object') {
            if (param.time.year !== undefined) {
                timeStr = `${param.time.year}-${String(param.time.month).padStart(2, '0')}-${String(param.time.day).padStart(2, '0')}`;
            } else if (param.time instanceof Date) {
                timeStr = param.time.toISOString().split('T')[0];
            }
        }
        
        const match = totalCandles.find(c => {
            const cleanCandleTime = c.timestamp.split('T')[0].replace(/\//g, '-');
            return cleanCandleTime === timeStr;
        });
        
        if (match) {
            const idx = totalCandles.indexOf(match);
            const prevCl = idx > 0 ? totalCandles[idx - 1].close : match.open;
            updateTradingViewInfoText(match, prevCl);
        }
    });
}

// Render Top 1 Stock Sparkline
function renderHeroChart(stock) {
    const container = document.getElementById('hero-recommendation-chart');
    container.innerHTML = '';
    
    const colors = getThemeColors();
    
    const chartOptions = {
        width: container.clientWidth || 360,
        height: 200,
        layout: {
            background: { type: 'solid', color: 'transparent' },
            textColor: colors.text,
            fontFamily: 'Inter',
        },
        grid: {
            horzLines: { visible: false },
            vertLines: { visible: false }
        },
        rightPriceScale: {
            visible: true,
            borderVisible: false,
        },
        timeScale: {
            visible: true,
            borderVisible: false,
        },
        crosshair: {
            vertLine: { visible: false },
            horzLine: { visible: false }
        },
        handleScroll: false,
        handleScale: false,
    };
    
    heroChart = LightweightCharts.createChart(container, chartOptions);
    
    const isUp = stock.trend === 'up';
    const colorLine = isUp ? colors.candleUp : colors.candleDown;
    const colorTop = isUp ? 'rgba(38, 166, 81, 0.25)' : 'rgba(229, 83, 75, 0.25)';
    
    heroAreaSeries = heroChart.addAreaSeries({
        lineColor: colorLine,
        topColor: colorTop,
        bottomColor: 'rgba(0, 0, 0, 0)',
        lineWidth: 2,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
    });
    
    // Last 30 history points + 5 forecast closes
    const histPart = stock.sparkline_candles.filter(c => !c.fcst);
    const fcPart = stock.sparkline_candles.filter(c => c.fcst);
    
    // Simulate dates for plotting
    const today = new Date();
    const points = [];
    
    // history
    for (let i = 0; i < histPart.length; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() - (histPart.length - i));
        points.push({
            time: d.toISOString().split('T')[0],
            value: histPart[i].close
        });
    }
    
    // forecast
    for (let i = 0; i < fcPart.length; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() + i);
        points.push({
            time: d.toISOString().split('T')[0],
            value: fcPart[i].close
        });
    }
    
    heroAreaSeries.setData(points);
    heroChart.timeScale().fitContent();
}

// Render Backtest Fold compare chart using Lightweight charts LineSeries
function renderBacktestFoldChart() {
    const container = document.getElementById('backtest-fold-chart');
    if (!container) return;
    container.innerHTML = '';
    
    const colors = getThemeColors();
    
    const chartOptions = {
        width: container.clientWidth || 700,
        height: 280,
        layout: {
            background: { type: 'solid', color: colors.background },
            textColor: colors.text,
            fontFamily: 'Inter',
        },
        grid: {
            horzLines: { color: colors.grid },
            vertLines: { color: colors.grid }
        },
        rightPriceScale: {
            borderColor: colors.grid,
            visible: true,
        },
        timeScale: {
            borderColor: colors.grid,
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        }
    };
    
    backtestChart = LightweightCharts.createChart(container, chartOptions);
    
    // Choose data source
    const useData = (reportsData && reportsData.yearly_compare && reportsData.yearly_compare.length > 0) 
        ? reportsData.yearly_compare 
        : WALK_FORWARD_DATA;
    
    // Line 1: Kronos FT (Thick blue)
    const ftSeries = backtestChart.addLineSeries({
        color: colors.meanPath,
        lineWidth: 3,
        title: 'Kronos Fine-tuned'
    });
    ftSeries.setData(useData.map(d => ({ time: d.fold + '-01-01', value: d.kronosFT })));

    // Line 2: Kronos ZS (Light blue dashed)
    const zsSeries = backtestChart.addLineSeries({
        color: '#6cb8ff',
        lineWidth: 1.5,
        lineStyle: LightweightCharts.LineStyle.Dashed,
        title: 'Kronos Zero-shot'
    });
    zsSeries.setData(useData.map(d => ({ time: d.fold + '-01-01', value: d.kronosZS })));

    // Line 3: Naive (gray)
    const naiveSeries = backtestChart.addLineSeries({
        color: '#8b949e',
        lineWidth: 1,
        title: 'Naive forecast'
    });
    naiveSeries.setData(useData.map(d => ({ time: d.fold + '-01-01', value: d.naive })));

    // Line 4: SMA (yellow)
    const smaSeries = backtestChart.addLineSeries({
        color: '#d29922',
        lineWidth: 1,
        title: 'SMA baseline'
    });
    smaSeries.setData(useData.map(d => ({ time: d.fold + '-01-01', value: d.sma })));
    
    backtestChart.timeScale().fitContent();
}

// Show/Hide global loading overlay
function showLoading(text) {
    loadingText.textContent = text;
    loadingOverlay.style.display = 'flex';
}

// Hàm tải báo cáo real
async function loadPerformanceReports() {
    try {
        const response = await fetch('/api/reports');
        const data = await response.json();
        if (data.success) {
            reportsData = data;
        }
    } catch (e) {
        console.error('Failed to load performance reports:', e);
    }
}

// Hàm chạy dự báo toàn bộ
async function runPredictAll() {
    try {
        const statusRes = await fetch('/api/model-status');
        const statusData = await statusRes.json();
        if (!statusData.loaded) {
            showToast("Mô hình chưa được nạp. Vui lòng vào Cài đặt và bấm 'Nạp mô hình' trước.", 'warning');
            switchTab('settings');
            return;
        }
    } catch (err) {
        console.error("Failed to check model status:", err);
    }

    showLoading("Đang chạy dự báo cho toàn bộ 50 cổ phiếu...\nTiến trình này chạy trên CPU và mất khoảng vài phút. Vui lòng không đóng tab.");
    try {
        const response = await fetch('/api/predict-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lookback: 126,
                pred_len: 5,
                temperature: parseFloat(tempInput.value),
                top_p: parseFloat(topPInput.value),
                sample_count: parseInt(samplesInput.value)
            })
        });
        
        if (response.status === 409) {
            showToast("Mô hình chưa được nạp. Vui lòng bấm 'Nạp mô hình' trong Cài đặt trước.", 'warning');
            return;
        }
        
        const data = await response.json();
        if (data.success) {
            showToast(data.message || "Đã hoàn thành dự báo cho toàn bộ rổ VN50!", 'success');
            await initApp();
        } else {
            showToast("Lỗi chạy dự báo rổ: " + (data.detail || data.error), 'error');
        }
    } catch (e) {
        console.error(e);
        showToast("Lỗi kết nối server khi chạy dự báo", 'error');
    } finally {
        hideLoading();
    }
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
}

// Resize handlers
window.addEventListener('resize', () => {
    if (detailsChart && currentTab === 'details') {
        const container = document.getElementById('details-forecast-chart');
        if (container) detailsChart.resize(container.clientWidth, 430);
    }
    if (heroChart && currentTab === 'overview') {
        const container = document.getElementById('hero-recommendation-chart');
        if (container) heroChart.resize(container.clientWidth, 200);
    }
    if (backtestChart && currentTab === 'backtest') {
        const container = document.getElementById('backtest-fold-chart');
        if (container) backtestChart.resize(container.clientWidth, 280);
    }
});

// Bind predict all buttons
if (bannerPredictAllBtn) bannerPredictAllBtn.addEventListener('click', runPredictAll);
if (settingsPredictAllBtn) settingsPredictAllBtn.addEventListener('click', runPredictAll);

// Start App
initApp();
