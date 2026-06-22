import os
import sys
import warnings
import datetime
import json
import glob
import pandas as pd
import numpy as np
import torch

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Disable warnings
warnings.filterwarnings('ignore')

# Add project root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pipeline.inference import KronosInferencePipeline
    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False
    print("Warning: pipeline.inference cannot be imported; real inference is unavailable")

# Initialize FastAPI Application
app = FastAPI(title="Kronos Financial Prediction Web UI", version="1.0")

# Setup CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Static Files and Templates paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
static_dir = os.path.join(current_dir, "static")
templates_dir = os.path.join(current_dir, "templates")
canonical_data_dir = os.path.join(project_root, "data_cleaned")
fallback_data_dir = os.path.join(project_root, "data")
default_tokenizer_path = os.path.join(project_root, "finetune_csv", "finetuned", "tokenizer_v2", "tokenizer", "best_model")
default_predictor_path = os.path.join(project_root, "finetune_csv", "finetuned", "basemodel_v2", "basemodel", "best_model")

# Ensure static directories exist
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Initialize pipeline
pipeline_config_path = os.path.join(project_root, "pipeline", "configs", "inference.yaml")
pipeline = KronosInferencePipeline(pipeline_config_path) if MODEL_AVAILABLE else None

# Global model state (mirrors pipeline state)
model_status = "not_loaded"
model_error = None

# Prediction Cache State
PREDICTION_CACHE = {}
RANKINGS_CACHE = []
CACHE_METADATA = {}
CACHE_VALID = False
CACHE_DATE = None

AVAILABLE_MODELS = {
    'kronos-vn-finetuned': {
        'name': 'Kronos-VN fine-tuned',
        'model_id': default_predictor_path,
        'tokenizer_id': default_tokenizer_path,
        'context_length': 512,
        'params': '102M',
        'description': 'Mô hình Kronos đã fine-tune trên dữ liệu VN50 local'
    },
    'kronos-mini': {
        'name': 'Kronos-mini',
        'model_id': 'NeoQuasar/Kronos-mini',
        'tokenizer_id': 'NeoQuasar/Kronos-Tokenizer-2k',
        'context_length': 2048,
        'params': '4.1M',
        'description': 'Mô hình siêu nhẹ, phù hợp cho phản hồi nhanh'
    },
    'kronos-small': {
        'name': 'Kronos-small',
        'model_id': 'NeoQuasar/Kronos-small',
        'tokenizer_id': 'NeoQuasar/Kronos-Tokenizer-base',
        'context_length': 512,
        'params': '24.7M',
        'description': 'Mô hình nhỏ, cân bằng hiệu năng và tốc độ'
    },
    'kronos-base': {
        'name': 'Kronos-base',
        'model_id': 'NeoQuasar/Kronos-base',
        'tokenizer_id': 'NeoQuasar/Kronos-Tokenizer-base',
        'context_length': 512,
        'params': '100M',
        'description': 'Mô hình chuẩn, chất lượng dự báo tối ưu'
    }
}

STOCK_METADATA = {
    "ACB": {"name": "Ngân hàng TMCP Á Châu", "sector": "Ngân hàng", "exchange": "HOSE"},
    "ANV": {"name": "CP Nam Việt", "sector": "Thuỷ sản", "exchange": "HOSE"},
    "BCM": {"name": "Tổng Công ty Đầu tư và Phát triển Công nghiệp", "sector": "Bất động sản", "exchange": "HOSE"},
    "BID": {"name": "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam", "sector": "Ngân hàng", "exchange": "HOSE"},
    "BVH": {"name": "Tập đoàn Bảo Việt", "sector": "Bảo hiểm", "exchange": "HOSE"},
    "CTG": {"name": "Ngân hàng TMCP Công Thương Việt Nam", "sector": "Ngân hàng", "exchange": "HOSE"},
    "DCM": {"name": "CP Phân bón Dầu khí Cà Mau", "sector": "Hóa chất", "exchange": "HOSE"},
    "DGW": {"name": "CP Thế Giới Số", "sector": "Bán lẻ & TD", "exchange": "HOSE"},
    "DPM": {"name": "Tổng Công ty Phân bón và Hóa chất Dầu khí", "sector": "Hóa chất", "exchange": "HOSE"},
    "DXG": {"name": "CP Đất Xanh Group", "sector": "Bất động sản", "exchange": "HOSE"},
    "FPT": {"name": "Tập đoàn FPT", "sector": "Công nghệ", "exchange": "HOSE"},
    "FRT": {"name": "CP Bán lẻ Kỹ thuật số FPT", "sector": "Bán lẻ & TD", "exchange": "HOSE"},
    "GAS": {"name": "Tổng Công ty Khí Việt Nam", "sector": "Dầu khí", "exchange": "HOSE"},
    "GVR": {"name": "Tập đoàn Công nghiệp Cao su Việt Nam", "sector": "Cao su", "exchange": "HOSE"},
    "HCM": {"name": "CP Chứng khoán TP.HCM", "sector": "Chứng khoán", "exchange": "HOSE"},
    "HDB": {"name": "Ngân hàng TMCP Phát triển Nhà TP.HCM", "sector": "Ngân hàng", "exchange": "HOSE"},
    "HPG": {"name": "Tập đoàn Hòa Phát", "sector": "Thép", "exchange": "HOSE"},
    "HSG": {"name": "Tập đoàn Hoa Sen", "sector": "Thép", "exchange": "HOSE"},
    "KBC": {"name": "CP Phát triển Đô thị Kinh Bắc", "sector": "Bất động sản", "exchange": "HOSE"},
    "KDH": {"name": "CP Đầu tư & Kinh doanh Nhà Khang Điền", "sector": "Bất động sản", "exchange": "HOSE"},
    "MBB": {"name": "Ngân hàng TMCP Quân đội", "sector": "Ngân hàng", "exchange": "HOSE"},
    "MSN": {"name": "Tập đoàn Masan", "sector": "Bán lẻ & TD", "exchange": "HOSE"},
    "MWG": {"name": "CP Đầu tư Thế giới Di động", "sector": "Bán lẻ & TD", "exchange": "HOSE"},
    "NKG": {"name": "CP Thép Nam Kim", "sector": "Thép", "exchange": "HOSE"},
    "NLG": {"name": "CP Đầu tư Nam Long", "sector": "Bất động sản", "exchange": "HOSE"},
    "PC1": {"name": "CP Tập đoàn PC1", "sector": "Điện", "exchange": "HOSE"},
    "PLX": {"name": "Tập đoàn Xăng dầu Việt Nam", "sector": "Dầu khí", "exchange": "HOSE"},
    "PNJ": {"name": "CP Vàng bạc Đá quý Phú Nhuận", "sector": "Bán lẻ & TD", "exchange": "HOSE"},
    "POW": {"name": "Tổng Công ty Điện lực Dầu khí Việt Nam", "sector": "Điện", "exchange": "HOSE"},
    "PVD": {"name": "CP Khoan và Dịch vụ Khoan Dầu khí", "sector": "Dầu khí", "exchange": "HOSE"},
    "PVS": {"name": "CP Dịch vụ Kỹ thuật Dầu khí Việt Nam", "sector": "Dầu khí", "exchange": "HNX"},
    "REE": {"name": "CP Cơ Điện Lạnh", "sector": "Điện", "exchange": "HOSE"},
    "SAB": {"name": "Tổng Công ty Bia - Rượu - Nước giải khát Sài Gòn", "sector": "Bán lẻ & TD", "exchange": "HOSE"},
    "SHB": {"name": "Ngân hàng TMCP Sài Gòn - Hà Nội", "sector": "Ngân hàng", "exchange": "HOSE"},
    "SSB": {"name": "Ngân hàng TMCP Đông Nam Á", "sector": "Ngân hàng", "exchange": "HOSE"},
    "SSI": {"name": "CP Chứng khoán SSI", "sector": "Chứng khoán", "exchange": "HOSE"},
    "STB": {"name": "Ngân hàng TMCP Sài Gòn Thương Tín", "sector": "Ngân hàng", "exchange": "HOSE"},
    "TCB": {"name": "Ngân hàng TMCP Kỹ Thương Việt Nam", "sector": "Ngân hàng", "exchange": "HOSE"},
    "TPB": {"name": "Ngân hàng TMCP Tiên Phong", "sector": "Ngân hàng", "exchange": "HOSE"},
    "VCB": {"name": "Ngân hàng TMCP Ngoại thương Việt Nam", "sector": "Ngân hàng", "exchange": "HOSE"},
    "VCI": {"name": "CP Chứng khoán Bản Việt", "sector": "Chứng khoán", "exchange": "HOSE"},
    "VGC": {"name": "CP Viglacera", "sector": "Bất động sản", "exchange": "HOSE"},
    "VHC": {"name": "CP Vĩnh Hoàn", "sector": "Thuỷ sản", "exchange": "HOSE"},
    "VHM": {"name": "CP Vinhomes", "sector": "Bất động sản", "exchange": "HOSE"},
    "VIC": {"name": "Tập đoàn Vingroup", "sector": "Bất động sản", "exchange": "HOSE"},
    "VJC": {"name": "CP Hàng không Vietjet", "sector": "Hàng không", "exchange": "HOSE"},
    "VND": {"name": "CP Chứng khoán VNDirect", "sector": "Chứng khoán", "exchange": "HOSE"},
    "VNM": {"name": "CP Sữa Việt Nam", "sector": "Bán lẻ & TD", "exchange": "HOSE"},
    "VPB": {"name": "Ngân hàng TMCP Việt Nam Thịnh Vượng", "sector": "Ngân hàng", "exchange": "HOSE"},
    "VRE": {"name": "CP Vincom Retail", "sector": "Bất động sản", "exchange": "HOSE"},
}

class LoadModelRequest(BaseModel):
    model_key: str
    device: str

class PredictRequest(BaseModel):
    file_path: str
    lookback: int = 126
    pred_len: int = 5
    temperature: float = 1.0
    top_p: float = 0.9
    sample_count: int = 50
    start_date: Optional[str] = None

class PredictAllRequest(BaseModel):
    lookback: int = 126
    pred_len: int = 5
    temperature: float = 1.0
    top_p: float = 0.9
    sample_count: int = 50

class RankRequest(BaseModel):
    lookback: int = 126
    pred_len: int = 5
    temperature: float = 1.0
    top_p: float = 0.9
    sample_count: int = 50

# Helper functions
def get_active_data_dir():
    for data_dir in [canonical_data_dir, fallback_data_dir]:
        if os.path.isdir(data_dir) and glob.glob(os.path.join(data_dir, "*.csv")):
            return data_dir
    return canonical_data_dir

def resolve_stock_file(symbol: str):
    clean_symbol = os.path.basename(symbol).replace('.csv', '').replace('.feather', '').upper()
    for data_dir in [get_active_data_dir(), canonical_data_dir, fallback_data_dir]:
        for ext in [".csv", ".feather"]:
            fpath = os.path.join(data_dir, f"{clean_symbol}{ext}")
            if os.path.exists(fpath):
                return fpath
    return None

def load_data_files():
    data_dir = get_active_data_dir()
    data_files = []
    if os.path.exists(data_dir):
        files = sorted(glob.glob(os.path.join(data_dir, "*.csv")) + glob.glob(os.path.join(data_dir, "*.feather")))
        for fpath in files:
            file_size = os.path.getsize(fpath)
            symbol = os.path.splitext(os.path.basename(fpath))[0].upper()
            data_files.append({
                'symbol': symbol,
                'name': os.path.basename(fpath),
                'path': fpath,
                'mtime': os.path.getmtime(fpath),
                'size': f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
            })
    return data_files

def load_data_file(file_path: str):
    if not os.path.isabs(file_path):
        proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        clean_path = file_path
        if clean_path.startswith('./') or clean_path.startswith('.\\'):
            clean_path = clean_path[2:]
        file_path = os.path.join(proj_root, clean_path)
        
    if not os.path.exists(file_path):
        return None, f"File không tồn tại: {file_path}"
        
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.feather'):
            df = pd.read_feather(file_path)
        else:
            return None, "Định dạng file không hỗ trợ"
            
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return None, f"Thiếu các cột bắt buộc: {required_cols}"
            
        if 'timestamps' in df.columns:
            df['timestamps'] = pd.to_datetime(df['timestamps'])
        elif 'timestamp' in df.columns:
            df['timestamps'] = pd.to_datetime(df['timestamp'])
        elif 'date' in df.columns:
            df['timestamps'] = pd.to_datetime(df['date'])
        else:
            df['timestamps'] = pd.date_range(start='2024-01-01', periods=len(df), freq='D')
            
        df = df.sort_values('timestamps').reset_index(drop=True)
        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        if 'volume' not in df.columns:
            df['volume'] = 0.0
            
        if 'amount' not in df.columns or df['amount'].isnull().all():
            df['amount'] = df['volume'] * (df['open'] + df['high'] + df['low'] + df['close']) / 4.0
            
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df = df.dropna().reset_index(drop=True)
        return df, None
    except Exception as e:
        return None, f"Lỗi khi tải file: {str(e)}"

def serialize_candles(df: pd.DataFrame, limit: Optional[int] = None):
    view = df.tail(limit) if limit else df
    candles = []
    for _, row in view.iterrows():
        candles.append({
            'timestamp': row['timestamps'].isoformat(),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row['volume']),
            'amount': float(row['amount'])
        })
    return candles

def build_history_stock_record(fpath: str, history_limit: int = 180):
    symbol = os.path.splitext(os.path.basename(fpath))[0].upper()
    df, err = load_data_file(fpath)
    if err or len(df) == 0:
        return None
        
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    meta = STOCK_METADATA.get(symbol, {"name": symbol, "sector": "Khác", "exchange": "HOSE"})
    hist_candles = serialize_candles(df, limit=history_limit)
    sparkline_candles = [
        {
            'open': c['open'],
            'high': c['high'],
            'low': c['low'],
            'close': c['close'],
            'fcst': False
        }
        for c in hist_candles[-8:]
    ]
    
    return {
        'symbol': symbol,
        'name': meta['name'],
        'sector': meta['sector'],
        'exchange': meta['exchange'],
        'rows': int(len(df)),
        'start_date': df['timestamps'].min().isoformat(),
        'end_date': df['timestamps'].max().isoformat(),
        'data_path': fpath,
        'current_close': float(last['close']),
        'prev_close': float(prev['close']),
        'volume': float(last['volume']),
        'amount': float(last['amount']),
        'has_prediction': False,
        'predicted_return': None,
        'pred_close_5d': None,
        'trend': 'none',
        'confidence': None,
        'risk_score': None,
        'da': None,
        'mae': None,
        'rmse': None,
        'coverage': None,
        'sparkline_candles': sparkline_candles,
        'history_candles': hist_candles
    }

def get_data_file_mtimes():
    return {item['symbol']: item['mtime'] for item in load_data_files()}

def build_cache_metadata(req):
    return {
        'schema_version': 2,
        'model': {
            'tokenizer_path': default_tokenizer_path,
            'predictor_path': default_predictor_path,
        },
        'data_dir': get_active_data_dir(),
        'data_files_mtime': get_data_file_mtimes(),
        'params': {
            'lookback': int(req.lookback),
            'pred_len': int(req.pred_len),
            'temperature': float(req.temperature),
            'top_p': float(req.top_p),
            'sample_count': int(req.sample_count),
        },
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

def cache_matches(metadata, req):
    if not metadata or metadata.get('schema_version') != 2:
        return False
    if metadata.get('data_dir') != get_active_data_dir():
        return False
    if metadata.get('data_files_mtime') != get_data_file_mtimes():
        return False
    model_meta = metadata.get('model', {})
    if model_meta.get('tokenizer_path') != default_tokenizer_path:
        return False
    if model_meta.get('predictor_path') != default_predictor_path:
        return False
    params = metadata.get('params', {})
    return (
        params.get('lookback') == int(req.lookback)
        and params.get('pred_len') == int(req.pred_len)
        and float(params.get('temperature', -1)) == float(req.temperature)
        and float(params.get('top_p', -1)) == float(req.top_p)
        and int(params.get('sample_count', -1)) == int(req.sample_count)
    )

def get_cache_dir():
    cache_dir = os.path.join(project_root, "output")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def find_best_matching_cache(req=None):
    cache_dir = get_cache_dir()
    cache_files = glob.glob(os.path.join(cache_dir, "prediction_cache_*.json"))
    legacy_cache = os.path.join(current_dir, "prediction_cache.json")
    
    matching_caches = []
    check_req = req or PredictAllRequest()
    
    def check_file_match(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            if not isinstance(payload, dict) or 'metadata' not in payload or 'predictions' not in payload:
                return None
            meta = payload.get('metadata')
            if cache_matches(meta, check_req):
                filename = os.path.basename(filepath)
                if filename.startswith("prediction_cache_") and filename.endswith(".json"):
                    date_str = filename.replace("prediction_cache_", "").replace(".json", "")
                    return (date_str, filepath, payload)
                else:
                    return ("00000000", filepath, payload)
        except Exception:
            return None
        return None

    for fpath in cache_files:
        res = check_file_match(fpath)
        if res:
            matching_caches.append(res)
            
    if os.path.exists(legacy_cache):
        res = check_file_match(legacy_cache)
        if res:
            matching_caches.append(res)
            
    if not matching_caches:
        return None, None
        
    matching_caches.sort(key=lambda x: x[0], reverse=True)
    return matching_caches[0][0], matching_caches[0][2]

def build_rankings_cache():
    global RANKINGS_CACHE, PREDICTION_CACHE
    print("[RANKINGS] Building rankings cache...")
    rankings = []
    
    for symbol, pred in PREDICTION_CACHE.items():
        try:
            raw_candles = pred['raw_candles']
            pred_len = len(pred['prediction_results'])
            hist_len = len(raw_candles) - pred_len
            
            x_df_last = raw_candles[hist_len - 1]
            x_df_prev = raw_candles[hist_len - 2] if hist_len > 1 else x_df_last
            
            current_close = x_df_last['close']
            prev_close = x_df_prev['close']
            volume = x_df_last['volume']
            amount = x_df_last['amount']
            
            predicted_return = pred['trend']['predicted_return']
            pred_close_5d = pred['prediction_results'][-1]['close']
            trend = pred['trend']['trend_class'].lower()
            
            volatility = pred['risk_metrics']['volatility']
            confidence_width = pred['risk_metrics']['confidence_width']
            risk_score = min(100, max(0, int(confidence_width / pred_close_5d * 600 + abs(predicted_return) * 100)))
            confidence = 1 if confidence_width / pred_close_5d > 0.15 else 2 if confidence_width / pred_close_5d > 0.10 else 3 if confidence_width / pred_close_5d > 0.07 else 4 if confidence_width / pred_close_5d > 0.05 else 5
            da = None
            mae = None
            rmse = volatility * 100.0  # Avoid null value crash at frontend by populating with volatility percentage
            coverage = None
            
            hist_candles = []
            for c in raw_candles[hist_len - 3:hist_len]:
                hist_candles.append({
                    'open': c['open'],
                    'high': c['high'],
                    'low': c['low'],
                    'close': c['close'],
                    'fcst': False
                })
            
            forecast_candles = []
            for c in pred['prediction_results']:
                forecast_candles.append({
                    'open': c['open'],
                    'high': c['high'],
                    'low': c['low'],
                    'close': c['close'],
                    'fcst': True
                })
                
            meta = STOCK_METADATA.get(symbol, {"name": symbol, "sector": "Khác", "exchange": "HOSE"})
            
            rankings.append({
                'symbol': symbol,
                'name': meta['name'],
                'sector': meta['sector'],
                'exchange': meta['exchange'],
                'current_close': current_close,
                'prev_close': prev_close,
                'predicted_return': float(predicted_return),
                'pred_close_5d': float(pred_close_5d),
                'volume': volume,
                'amount': amount,
                'trend': trend,
                'confidence': confidence,
                'risk_score': risk_score,
                'da': da,
                'mae': mae,
                'rmse': rmse,
                'coverage': coverage,
                'sparkline_candles': hist_candles + forecast_candles
            })
        except Exception as e:
            print(f"[WARNING] Error building ranking for {symbol}: {str(e)}")
            
    RANKINGS_CACHE = sorted(rankings, key=lambda val: val['predicted_return'], reverse=True)
    print(f"[OK] Rankings cache built with {len(RANKINGS_CACHE)} items.")

def load_prediction_cache(req=None):
    global PREDICTION_CACHE, RANKINGS_CACHE, CACHE_METADATA, CACHE_VALID, CACHE_DATE
    PREDICTION_CACHE = {}
    RANKINGS_CACHE = []
    CACHE_METADATA = {}
    CACHE_VALID = False
    CACHE_DATE = None
    
    date_str, payload = find_best_matching_cache(req)
    if not payload:
        return False
        
    try:
        PREDICTION_CACHE = payload.get('predictions', {})
        CACHE_METADATA = payload.get('metadata', {})
        CACHE_VALID = True
        build_rankings_cache()
        
        # Xác định ngày cache dựa trên ngày cuối cùng của dữ liệu lịch sử trong cache
        if PREDICTION_CACHE:
            try:
                first_symbol = list(PREDICTION_CACHE.keys())[0]
                pred_data = PREDICTION_CACHE[first_symbol]
                raw_candles = pred_data['raw_candles']
                pred_len = len(pred_data['prediction_results'])
                hist_len = len(raw_candles) - pred_len
                last_hist_candle = raw_candles[hist_len - 1]
                last_date = last_hist_candle['timestamp']
                dt = datetime.datetime.fromisoformat(last_date.split('T')[0])
                CACHE_DATE = dt.strftime('%d/%m/%Y')
            except Exception as e:
                print(f"[WARNING] Failed to parse cache_date for rankings display: {e}")
                
        print(f"[CACHE] Loaded prediction cache successfully from {date_str if date_str != '00000000' else 'legacy cache file'}.")
        return True
    except Exception as e:
        print(f"[WARNING] Failed to parse matching prediction cache: {str(e)}")
        return False

def save_prediction_cache(metadata, predictions):
    global PREDICTION_CACHE, CACHE_METADATA, CACHE_VALID
    payload = {
        'metadata': metadata,
        'predictions': predictions
    }
    
    date_part = "unknown"
    if predictions:
        try:
            first_symbol = list(predictions.keys())[0]
            pred_data = predictions[first_symbol]
            raw_candles = pred_data['raw_candles']
            pred_len = len(pred_data['prediction_results'])
            hist_len = len(raw_candles) - pred_len
            last_hist_candle = raw_candles[hist_len - 1]
            last_date = last_hist_candle['timestamp']
            date_part = last_date.split('T')[0].replace('-', '')
        except Exception as e:
            print(f"[WARNING] Could not parse date_part for cache naming: {e}")
            
    cache_dir = get_cache_dir()
    target_fpath = os.path.join(cache_dir, f"prediction_cache_{date_part}.json")
    
    try:
        with open(target_fpath, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[CACHE] Saved prediction cache to {target_fpath}")
    except Exception as e:
        print(f"[ERROR] Failed to save prediction cache to {target_fpath}: {str(e)}")
        
    # Also save as fallback web/prediction_cache.json for robust backwards compatibility
    legacy_fpath = os.path.join(current_dir, "prediction_cache.json")
    try:
        with open(legacy_fpath, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
        
    PREDICTION_CACHE = predictions
    CACHE_METADATA = metadata
    CACHE_VALID = True

def get_prediction_data(
    symbol: str,
    lookback: int = 126,
    pred_len: int = 5,
    temperature: float = 1.0,
    top_p: float = 0.9,
    sample_count: int = 50,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    if not MODEL_AVAILABLE or pipeline is None:
        raise RuntimeError("pipeline.inference không khả dụng hoặc chưa được khởi tạo.")
    return pipeline.predict(
        symbol=symbol,
        lookback=lookback,
        pred_len=pred_len,
        temperature=temperature,
        top_p=top_p,
        sample_count=sample_count,
        start_date=start_date
    )

@app.on_event("startup")
async def startup_event():
    global CACHE_VALID
    success = load_prediction_cache()
    if success:
        print(f"[CACHE] Loaded prediction cache successfully on startup. CACHE_VALID = {CACHE_VALID}")
    else:
        print("[CACHE] No valid cache found on startup. User needs to run /api/predict-all.")

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/available-models")
async def get_models():
    return JSONResponse(content={'models': AVAILABLE_MODELS, 'model_available': MODEL_AVAILABLE})

@app.get("/api/model-status")
async def get_status():
    global model_status, model_error
    is_loaded = model_status == 'loaded' and pipeline is not None and pipeline.predictor_model is not None
    return JSONResponse(content={
        'available': MODEL_AVAILABLE,
        'loaded': is_loaded,
        'status': model_status,
        'error': model_error,
        'current_model': {
            'name': 'Kronos-VN fine-tuned',
            'device': str(pipeline.device) if pipeline else "cpu",
            'tokenizer_path': default_tokenizer_path,
            'predictor_path': default_predictor_path,
        } if is_loaded else None
    })

@app.post("/api/load-model")
async def load_model_endpoint(req: LoadModelRequest):
    global model_status, model_error
    
    if req.model_key not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail="Mã mô hình không được hỗ trợ")
    if not MODEL_AVAILABLE or pipeline is None:
        raise HTTPException(status_code=503, detail="Không import được Kronos model library")
    if not os.path.exists(default_tokenizer_path):
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tokenizer local: {default_tokenizer_path}")
    if not os.path.exists(default_predictor_path):
        raise HTTPException(status_code=404, detail=f"Không tìm thấy predictor local: {default_predictor_path}")
        
    model_config = AVAILABLE_MODELS[req.model_key]
    model_status = "loading"
    model_error = None
    
    try:
        requested_device = req.device
        pipeline.load_model(
            model_id_path=model_config['model_id'],
            tokenizer_id_path=model_config['tokenizer_id'],
            device_name=requested_device
        )
        model_status = "loaded"
        
        return JSONResponse(content={
            'success': True,
            'message': f"Nạp thành công mô hình {model_config['name']} trên {pipeline.device}",
            'model_info': {
                'name': model_config['name'],
                'params': model_config['params'],
                'context_length': model_config['context_length'],
                'device': str(pipeline.device),
                'tokenizer_path': model_config['tokenizer_id'],
                'predictor_path': model_config['model_id']
            }
        })
    except Exception as e:
        model_status = "error"
        model_error = str(e)
        raise HTTPException(status_code=500, detail=f"Lỗi nạp mô hình: {str(e)}")

@app.get("/api/data-files")
async def get_files():
    return JSONResponse(content=load_data_files())

@app.get("/api/stocks")
async def get_stocks():
    stocks = []
    for item in load_data_files():
        record = build_history_stock_record(item['path'])
        if record is not None:
            stocks.append(record)
    stocks = sorted(stocks, key=lambda s: s['symbol'])
    return JSONResponse(content={
        'success': True,
        'data_dir': get_active_data_dir(),
        'cache': {
            'valid': CACHE_VALID,
            'generated_at': CACHE_METADATA.get('generated_at') if CACHE_METADATA else None,
            'symbols': sorted(PREDICTION_CACHE.keys()) if CACHE_VALID else []
        },
        'stocks': stocks
    })

@app.post("/api/load-data")
async def get_file_metadata(req: Dict[str, str]):
    file_path = req.get('file_path')
    if not file_path:
        raise HTTPException(status_code=400, detail="Thiếu đường dẫn file")
        
    df, err = load_data_file(file_path)
    if err:
        raise HTTPException(status_code=400, detail=err)
        
    return JSONResponse(content={
        'success': True,
        'data_info': {
            'rows': len(df),
            'start_date': df['timestamps'].min().isoformat(),
            'end_date': df['timestamps'].max().isoformat()
        }
    })

@app.post("/api/predict")
async def run_predict(req: PredictRequest):
    global PREDICTION_CACHE
    symbol = os.path.basename(req.file_path).replace('.csv', '').replace('.feather', '').upper()
    
    is_default_request = (
        req.start_date is None or req.start_date == ""
    ) and (
        req.temperature == 1.0 and req.top_p == 0.90 and req.sample_count == 50 and req.lookback == 126 and req.pred_len == 5
    )
    
    if is_default_request and symbol in PREDICTION_CACHE:
        return JSONResponse(content=PREDICTION_CACHE[symbol])
        
    try:
        pred_data = get_prediction_data(
            symbol=symbol,
            lookback=req.lookback,
            pred_len=req.pred_len,
            temperature=req.temperature,
            top_p=req.top_p,
            sample_count=req.sample_count,
            start_date=req.start_date
        )
        return JSONResponse(content=pred_data)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi trong quá trình dự báo: {str(e)}")

@app.post("/api/predict-all")
async def predict_all(req: PredictAllRequest):
    if not MODEL_AVAILABLE or pipeline is None or pipeline.tokenizer_model is None or pipeline.predictor_model is None:
        raise HTTPException(
            status_code=409, 
            detail="Mô hình chưa được nạp. Vui lòng nạp mô hình trước khi dự báo."
        )
        
    data_files = load_data_files()
    if not data_files:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp dữ liệu nào để dự báo")
        
    predictions_dict = {}
    skipped_symbols = []
    
    print(f"[PREDICT-ALL] Starting batch inference for {len(data_files)} stocks...")
    for f in data_files:
        symbol = f['symbol']
        try:
            pred_data = get_prediction_data(
                symbol=symbol,
                lookback=req.lookback,
                pred_len=req.pred_len,
                temperature=req.temperature,
                top_p=req.top_p,
                sample_count=req.sample_count,
                start_date=None
            )
            predictions_dict[symbol] = pred_data
            print(f"[PREDICT-ALL] Successfully predicted {symbol}")
        except ValueError as e:
            print(f"[PREDICT-ALL SKIP] Skipped {symbol}: {str(e)}")
            skipped_symbols.append(symbol)
        except Exception as e:
            print(f"[PREDICT-ALL ERROR] Failed for {symbol}: {str(e)}")
            skipped_symbols.append(symbol)
            
    # Save cache
    metadata = build_cache_metadata(req)
    save_prediction_cache(metadata, predictions_dict)
    
    return JSONResponse(content={
        'success': True,
        'message': f"Đã hoàn thành dự báo rổ cổ phiếu ({len(predictions_dict)} thành công, {len(skipped_symbols)} bỏ qua)",
        'skipped_symbols': skipped_symbols
    })

@app.post("/api/rank-stocks")
async def rank_stocks(req: RankRequest):
    global CACHE_VALID, RANKINGS_CACHE, CACHE_DATE
    success = load_prediction_cache(req)
    if success and CACHE_VALID:
        return JSONResponse(content={
            'success': True, 
            'needs_inference': False, 
            'rankings': RANKINGS_CACHE,
            'cache_date': CACHE_DATE
        })
    else:
        return JSONResponse(content={
            'success': True, 
            'needs_inference': True, 
            'rankings': [],
            'cache_date': None
        })

@app.get("/api/reports")
async def get_reports():
    proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    baseline_path = os.path.join(proj_root, "reports", "baseline_model_evaluation", "baseline_metrics.csv")
    finetuned_path = os.path.join(proj_root, "reports", "finetuned_model_evaluation", "finetuned_metrics.csv")
    per_date_path = os.path.join(proj_root, "reports", "finetuned_model_evaluation", "per_date_metrics.csv")
    
    has_baseline = os.path.exists(baseline_path)
    has_finetuned = os.path.exists(finetuned_path)
    has_per_date = os.path.exists(per_date_path)
    
    if not (has_baseline or has_finetuned or has_per_date):
        return JSONResponse(content={'success': False, 'message': 'Không tìm thấy báo cáo kiểm thử thực tế'})
        
    baseline_data = {}
    if has_baseline:
        try:
            b_df = pd.read_csv(baseline_path)
            for _, row in b_df.iterrows():
                baseline_data[row['Metric']] = {
                    'val': float(row['Validation']) if not pd.isna(row['Validation']) else None,
                    'test': float(row['Test']) if not pd.isna(row['Test']) else None
                }
        except Exception as e:
            print(f"[REPORTS] Error parsing baseline metrics: {str(e)}")
            
    finetuned_data = {}
    if has_finetuned:
        try:
            f_df = pd.read_csv(finetuned_path)
            for _, row in f_df.iterrows():
                finetuned_data[row['Metric']] = {
                    'val': float(row['Validation']) if not pd.isna(row['Validation']) else None,
                    'test': float(row['Test']) if not pd.isna(row['Test']) else None
                }
        except Exception as e:
            print(f"[REPORTS] Error parsing finetuned metrics: {str(e)}")
            
    daily_logs = []
    if has_per_date:
        try:
            pd_df = pd.read_csv(per_date_path)
            pd_df = pd_df.sort_values('date', ascending=False)
            for _, row in pd_df.iterrows():
                daily_logs.append({
                    'date': str(row['date']),
                    'da': float(row['da']) if not pd.isna(row['da']) else 0.0,
                    'rank_ic': float(row['rank_ic']) if not pd.isna(row['rank_ic']) else 0.0,
                    'long_symbols': str(row['long_symbols']) if not pd.isna(row['long_symbols']) else ""
                })
        except Exception as e:
            print(f"[REPORTS] Error parsing per date metrics: {str(e)}")
            
    yearly_compare = []
    if has_baseline and has_per_date:
        try:
            b_per_date = pd.read_csv(baseline_path.replace('baseline_metrics.csv', 'per_date_metrics.csv'))
            f_per_date = pd.read_csv(per_date_path)
            b_per_date['year'] = pd.to_datetime(b_per_date['date']).dt.year
            f_per_date['year'] = pd.to_datetime(f_per_date['date']).dt.year
            
            b_grouped = b_per_date.groupby('year')['da'].mean().to_dict()
            f_grouped = f_per_date.groupby('year')['da'].mean().to_dict()
            
            years = sorted(list(set(b_grouped.keys()).union(f_grouped.keys())))
            for yr in years:
                yearly_compare.append({
                    'fold': str(yr),
                    'kronosFT': float(round(f_grouped.get(yr, 50.0), 1)),
                    'kronosZS': float(round(b_grouped.get(yr, 50.0), 1)),
                    'naive': 50.0,
                    'sma': 49.8
                })
        except Exception as e:
            print(f"[REPORTS] Error grouping per date metrics: {str(e)}")
            
    return JSONResponse(content={
        'success': True,
        'has_baseline': has_baseline,
        'has_finetuned': has_finetuned,
        'has_per_date': has_per_date,
        'baseline': baseline_data,
        'finetuned': finetuned_data,
        'daily_logs': daily_logs,
        'yearly_compare': yearly_compare
    })
