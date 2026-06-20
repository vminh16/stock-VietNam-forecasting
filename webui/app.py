import os
import sys
import warnings
import datetime
import json
import glob
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

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
    from model import Kronos, KronosTokenizer, KronosPredictor
    from model.kronos import calc_time_stamps, sample_from_logits
    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False
    print("Warning: Kronos model cannot be imported, will use simulated data for fallback demonstration")

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
static_dir = os.path.join(current_dir, "static")
templates_dir = os.path.join(current_dir, "templates")

# Ensure static directories exist
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Global model pointers
tokenizer_model = None
predictor_model = None
predictor = None
device = "cpu"

AVAILABLE_MODELS = {
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
        'params': '102.3M',
        'description': 'Mô hình chuẩn, chất lượng dự báo tối ưu'
    }
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

class RankRequest(BaseModel):
    lookback: int = 126
    pred_len: int = 5
    temperature: float = 1.0
    top_p: float = 0.9

# Custom inference function to return all stochastic paths
def auto_regressive_inference_paths(tokenizer, model, x, x_stamp, y_stamp, max_context, pred_len, clip=5.0, T=1.0, top_k=0, top_p=0.90, sample_count=50):
    with torch.no_grad():
        x = torch.clip(x, -clip, clip)
        curr_device = x.device
        
        # Repeat input for multiple sample paths
        x = x.unsqueeze(1).repeat(1, sample_count, 1, 1).reshape(-1, x.size(1), x.size(2)).to(curr_device)
        x_stamp = x_stamp.unsqueeze(1).repeat(1, sample_count, 1, 1).reshape(-1, x_stamp.size(1), x_stamp.size(2)).to(curr_device)
        y_stamp = y_stamp.unsqueeze(1).repeat(1, sample_count, 1, 1).reshape(-1, y_stamp.size(1), y_stamp.size(2)).to(curr_device)

        x_token = tokenizer.encode(x, half=True)
        
        initial_seq_len = x.size(1)
        batch_size = x_token[0].size(0)
        total_seq_len = initial_seq_len + pred_len
        full_stamp = torch.cat([x_stamp, y_stamp], dim=1)

        generated_pre = x_token[0].new_empty(batch_size, pred_len)
        generated_post = x_token[1].new_empty(batch_size, pred_len)

        pre_buffer = x_token[0].new_zeros(batch_size, max_context)
        post_buffer = x_token[1].new_zeros(batch_size, max_context)
        buffer_len = min(initial_seq_len, max_context)
        if buffer_len > 0:
            start_idx = max(0, initial_seq_len - max_context)
            pre_buffer[:, :buffer_len] = x_token[0][:, start_idx:start_idx + buffer_len]
            post_buffer[:, :buffer_len] = x_token[1][:, start_idx:start_idx + buffer_len]

        for i in range(pred_len):
            current_seq_len = initial_seq_len + i
            window_len = min(current_seq_len, max_context)

            if current_seq_len <= max_context:
                input_tokens = [
                    pre_buffer[:, :window_len],
                    post_buffer[:, :window_len]
                ]
            else:
                input_tokens = [pre_buffer, post_buffer]

            context_end = current_seq_len
            context_start = max(0, context_end - max_context)
            current_stamp = full_stamp[:, context_start:context_end, :].contiguous()

            s1_logits, context = model.decode_s1(input_tokens[0], input_tokens[1], current_stamp)
            s1_logits = s1_logits[:, -1, :]
            sample_pre = sample_from_logits(s1_logits, temperature=T, top_k=top_k, top_p=top_p, sample_logits=True)

            s2_logits = model.decode_s2(context, sample_pre)
            s2_logits = s2_logits[:, -1, :]
            sample_post = sample_from_logits(s2_logits, temperature=T, top_k=top_k, top_p=top_p, sample_logits=True)

            generated_pre[:, i] = sample_pre.squeeze(-1)
            generated_post[:, i] = sample_post.squeeze(-1)

            if current_seq_len < max_context:
                pre_buffer[:, current_seq_len] = sample_pre.squeeze(-1)
                post_buffer[:, current_seq_len] = sample_post.squeeze(-1)
            else:
                pre_buffer.copy_(torch.roll(pre_buffer, shifts=-1, dims=1))
                post_buffer.copy_(torch.roll(post_buffer, shifts=-1, dims=1))
                pre_buffer[:, -1] = sample_pre.squeeze(-1)
                post_buffer[:, -1] = sample_post.squeeze(-1)

        full_pre = torch.cat([x_token[0], generated_pre], dim=1)
        full_post = torch.cat([x_token[1], generated_post], dim=1)

        context_start = max(0, total_seq_len - max_context)
        input_tokens = [
            full_pre[:, context_start:total_seq_len].contiguous(),
            full_post[:, context_start:total_seq_len].contiguous()
        ]
        z = tokenizer.decode(input_tokens, half=True)
        z = z.reshape(-1, sample_count, z.size(1), z.size(2))
        return z.cpu().numpy() # Shape: (1, sample_count, total_seq_len, features)

# Helper functions for calculations
def load_data_files():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    data_files = []
    
    if os.path.exists(data_dir):
        files = glob.glob(os.path.join(data_dir, "*.csv")) + glob.glob(os.path.join(data_dir, "*.feather"))
        for fpath in files:
            file_size = os.path.getsize(fpath)
            data_files.append({
                'name': os.path.basename(fpath),
                'path': fpath,
                'size': f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
            })
    return data_files

def load_data_file(file_path: str):
    if not os.path.exists(file_path):
        return None, "File không tồn tại"
        
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
            
        # Amount calculation guard
        if 'amount' not in df.columns or df['amount'].isnull().all():
            df['amount'] = df['volume'] * (df['open'] + df['high'] + df['low'] + df['close']) / 4.0
            
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        df = df.dropna().reset_index(drop=True)
        return df, None
    except Exception as e:
        return None, f"Lỗi khi tải file: {str(e)}"

# Endpoints
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/available-models")
async def get_models():
    return JSONResponse(content={'models': AVAILABLE_MODELS, 'model_available': MODEL_AVAILABLE})

@app.get("/api/model-status")
async def get_status():
    global predictor_model, device
    if MODEL_AVAILABLE and predictor_model is not None:
        return JSONResponse(content={
            'available': True,
            'loaded': True,
            'current_model': {
                'name': predictor_model.__class__.__name__,
                'device': str(device)
            }
        })
    return JSONResponse(content={
        'available': MODEL_AVAILABLE,
        'loaded': False,
        'message': 'Mô hình chưa được nạp'
    })

@app.post("/api/load-model")
async def load_model_endpoint(req: LoadModelRequest):
    global tokenizer_model, predictor_model, predictor, device
    
    if not MODEL_AVAILABLE:
        raise HTTPException(status_code=400, detail="Mô hình Kronos không có sẵn")
        
    if req.model_key not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail="Mã mô hình không được hỗ trợ")
        
    model_config = AVAILABLE_MODELS[req.model_key]
    device = req.device
    
    try:
        # Load weights
        tokenizer_model = KronosTokenizer.from_pretrained(model_config['tokenizer_id'])
        predictor_model = Kronos.from_pretrained(model_config['model_id'])
        
        tokenizer_model = tokenizer_model.to(device)
        predictor_model = predictor_model.to(device)
        
        predictor = KronosPredictor(predictor_model, tokenizer_model, device=device, max_context=model_config['context_length'])
        
        return JSONResponse(content={
            'success': True,
            'message': f"Nạp thành công {model_config['name']} trên {device}",
            'model_info': {
                'name': model_config['name'],
                'params': model_config['params'],
                'context_length': model_config['context_length']
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi nạp mô hình: {str(e)}")

@app.get("/api/data-files")
async def get_files():
    return JSONResponse(content=load_data_files())

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
    global predictor, tokenizer_model, predictor_model, device
    
    if not predictor:
        raise HTTPException(status_code=400, detail="Mô hình chưa được nạp. Hãy nạp mô hình trước.")
        
    df, err = load_data_file(req.file_path)
    if err:
        raise HTTPException(status_code=400, detail=err)
        
    if len(df) < req.lookback:
        raise HTTPException(status_code=400, detail=f"Dữ liệu lịch sử không đủ, cần tối thiểu {req.lookback} nến.")
        
    try:
        # Determine slice based on start_date
        if req.start_date:
            start_dt = pd.to_datetime(req.start_date)
            mask = df['timestamps'] >= start_dt
            time_range_df = df[mask]
            
            if len(time_range_df) < req.lookback + req.pred_len:
                raise HTTPException(status_code=400, detail=f"Không đủ {req.lookback + req.pred_len} nến tính từ ngày {req.start_date}")
                
            x_df = time_range_df.iloc[:req.lookback]
            actual_df = time_range_df.iloc[req.lookback:req.lookback+req.pred_len]
            has_comparison = True
        else:
            x_df = df.iloc[-req.lookback:]
            actual_df = pd.DataFrame()
            has_comparison = False

        price_cols = ['open', 'high', 'low', 'close']
        features = price_cols + ['volume', 'amount']
        
        # Prepare arrays for inference
        x_raw = x_df[features].values.astype(np.float64)
        x_mean = np.mean(x_raw, axis=0)
        x_std = np.std(x_raw, axis=0)
        x_std = np.where(x_std < 1e-6, 1.0, x_std)
        
        x_norm = (x_raw - x_mean) / (x_std + 1e-5)
        x_norm = np.clip(x_norm, -predictor.clip, predictor.clip)
        
        x_tensor = torch.from_numpy(x_norm[np.newaxis, ...].astype(np.float32)).to(device)
        
        # Generate timestamps
        x_timestamps = x_df['timestamps']
        if has_comparison:
            y_timestamps = actual_df['timestamps']
        else:
            time_diff = df['timestamps'].iloc[1] - df['timestamps'].iloc[0] if len(df) > 1 else pd.Timedelta(days=1)
            y_timestamps = pd.date_range(start=x_timestamps.iloc[-1] + time_diff, periods=req.pred_len, freq=time_diff)
            
        x_stamp_df = calc_time_stamps(pd.Series(x_timestamps))
        y_stamp_df = calc_time_stamps(pd.Series(y_timestamps))
        
        x_stamp_tensor = torch.from_numpy(x_stamp_df.values[np.newaxis, ...].astype(np.float32)).to(device)
        y_stamp_tensor = torch.from_numpy(y_stamp_df.values[np.newaxis, ...].astype(np.float32)).to(device)
        
        # 1. Run Stochastic Inference to get ALL paths
        paths_norm = auto_regressive_inference_paths(
            tokenizer_model, predictor_model, x_tensor, x_stamp_tensor, y_stamp_tensor,
            max_context=predictor.max_context, pred_len=req.pred_len, clip=predictor.clip,
            T=req.temperature, top_p=req.top_p, sample_count=req.sample_count
        )
        # paths_norm shape: (1, sample_count, total_seq_len, features)
        paths_norm = paths_norm.squeeze(0) # (sample_count, total_seq_len, features)
        
        # Extract only predicted portion
        pred_paths_norm = paths_norm[:, -req.pred_len:, :]
        
        # Denormalize all paths
        pred_paths_raw = pred_paths_norm * (x_std + 1e-5) + x_mean # (sample_count, pred_len, features)
        
        # 2. Calculate Mean Prediction Path
        mean_pred_raw = np.mean(pred_paths_raw, axis=0) # (pred_len, features)
        
        # 3. Calculate Risk Metrics on Close Price (Index 3) on last day
        close_samples = pred_paths_raw[:, -1, 3]
        volatility = float(np.std(close_samples) / np.mean(close_samples))
        var_5pct = float(np.percentile(close_samples, 5))
        var_95pct = float(np.percentile(close_samples, 95))
        confidence_width = float(var_95pct - var_5pct)
        
        # 4. Calculate Trend
        current_close = float(x_df.iloc[-1]['close'])
        pred_close_5d = float(mean_pred_raw[-1, 3])
        predicted_return = (pred_close_5d - current_close) / current_close
        
        trend_class = "SIDEWAY"
        if predicted_return > 0.03:
            trend_class = "UP"
        elif predicted_return < -0.03:
            trend_class = "DOWN"
            
        # 5. XAI Token Frequency Analysis
        # Fetch S1 tokens (coarse trend tokens) for historical window + mean prediction
        full_df_raw = np.concatenate([x_raw, mean_pred_raw], axis=0)
        full_norm = (full_df_raw - x_mean) / (x_std + 1e-5)
        full_norm = np.clip(full_norm, -predictor.clip, predictor.clip)
        full_tensor = torch.from_numpy(full_norm[np.newaxis, ...].astype(np.float32)).to(device)
        
        with torch.no_grad():
            z_indices = tokenizer_model.encode(full_tensor, half=True)
            # z_indices is a list of two tensors: [s1, s2]
            s1_tokens = z_indices[0].squeeze(0).cpu().numpy()
            
        # Count frequency of last 15 tokens
        last_s1 = s1_tokens[-15:].tolist()
        unique, counts = np.unique(last_s1, return_counts=True)
        xai_data = [{'token': int(t), 'frequency': int(c)} for t, c in zip(unique, counts)]
        xai_data = sorted(xai_data, key=lambda val: val['frequency'], reverse=True)
        
        # 6. Format Response
        # Reconstruct total display series for Plotly
        # History (126 nến) + Prediction (5 nến)
        raw_candles = []
        for idx, row in x_df.iterrows():
            raw_candles.append({
                'timestamp': row['timestamps'].isoformat(),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']),
                'amount': float(row['amount'])
            })
            
        prediction_results = []
        for i in range(req.pred_len):
            prediction_results.append({
                'timestamp': y_timestamps[i].isoformat(),
                'open': float(mean_pred_raw[i, 0]),
                'high': float(mean_pred_raw[i, 1]),
                'low': float(mean_pred_raw[i, 2]),
                'close': float(mean_pred_raw[i, 3]),
                'volume': float(mean_pred_raw[i, 4]),
                'amount': float(mean_pred_raw[i, 5])
            })
            
        # Append predictions to global display list for status line hover
        total_candles = raw_candles + prediction_results
        
        # Format stochastic paths for client
        stochastic_paths = []
        for p_idx in range(req.sample_count):
            path_candles = []
            for i in range(req.pred_len):
                path_candles.append(pred_paths_raw[p_idx, i].tolist())
            stochastic_paths.append(path_candles)
            
        actual_data = []
        if has_comparison:
            for idx, row in actual_df.iterrows():
                actual_data.append({
                    'timestamp': row['timestamps'].isoformat(),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume']),
                    'amount': float(row['amount'])
                })
                
        return JSONResponse(content={
            'success': True,
            'trend': {
                'trend_class': trend_class,
                'predicted_return': float(predicted_return)
            },
            'risk_metrics': {
                'volatility': volatility,
                'var_5pct': var_5pct,
                'confidence_width': confidence_width
            },
            'raw_candles': total_candles,
            'prediction_results': prediction_results,
            'actual_data': actual_data,
            'stochastic_paths': stochastic_paths,
            'has_comparison': has_comparison,
            'xai_data': xai_data
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi trong quá trình dự báo: {str(e)}")

@app.post("/api/rank-stocks")
async def rank_stocks(req: RankRequest):
    global predictor, tokenizer_model, predictor_model, device
    
    if not predictor:
        raise HTTPException(status_code=400, detail="Mô hình chưa được nạp. Hãy nạp mô hình trước.")
        
    data_files = load_data_files()
    if not data_files:
        return JSONResponse(content={'success': True, 'rankings': []})
        
    rankings = []
    price_cols = ['open', 'high', 'low', 'close']
    features = price_cols + ['volume', 'amount']
    
    for f in data_files:
        symbol = f['name'].replace('.csv', '').replace('.feather', '')
        df, err = load_data_file(f['path'])
        if err or len(df) < req.lookback:
            continue
            
        try:
            x_df = df.iloc[-req.lookback:]
            
            # Sub-sample setup
            x_raw = x_df[features].values.astype(np.float64)
            x_mean = np.mean(x_raw, axis=0)
            x_std = np.std(x_raw, axis=0)
            x_std = np.where(x_std < 1e-6, 1.0, x_std)
            
            x_norm = (x_raw - x_mean) / (x_std + 1e-5)
            x_norm = np.clip(x_norm, -predictor.clip, predictor.clip)
            
            x_tensor = torch.from_numpy(x_norm[np.newaxis, ...].astype(np.float32)).to(device)
            
            # Setup stamps
            time_diff = df['timestamps'].iloc[1] - df['timestamps'].iloc[0] if len(df) > 1 else pd.Timedelta(days=1)
            x_timestamps = x_df['timestamps']
            y_timestamps = pd.date_range(start=x_timestamps.iloc[-1] + time_diff, periods=req.pred_len, freq=time_diff)
            
            x_stamp_df = calc_time_stamps(pd.Series(x_timestamps))
            y_stamp_df = calc_time_stamps(pd.Series(y_timestamps))
            
            x_stamp_tensor = torch.from_numpy(x_stamp_df.values[np.newaxis, ...].astype(np.float32)).to(device)
            y_stamp_tensor = torch.from_numpy(y_stamp_df.values[np.newaxis, ...].astype(np.float32)).to(device)
            
            # Use small sample count = 5 for faster ranking calculation
            paths_norm = auto_regressive_inference_paths(
                tokenizer_model, predictor_model, x_tensor, x_stamp_tensor, y_stamp_tensor,
                max_context=predictor.max_context, pred_len=req.pred_len, clip=predictor.clip,
                T=req.temperature, top_p=req.top_p, sample_count=5
            )
            paths_norm = paths_norm.squeeze(0)
            pred_paths_norm = paths_norm[:, -req.pred_len:, :]
            pred_paths_raw = pred_paths_norm * (x_std + 1e-5) + x_mean
            
            mean_pred_raw = np.mean(pred_paths_raw, axis=0)
            
            current_close = float(x_df.iloc[-1]['close'])
            pred_close_5d = float(mean_pred_raw[-1, 3])
            predicted_return = (pred_close_5d - current_close) / current_close
            
            rankings.append({
                'symbol': symbol,
                'file_path': f['path'],
                'predicted_return': float(predicted_return),
                'current_close': current_close,
                'pred_close_5d': pred_close_5d
            })
        except Exception as e:
            # Skip corrupted stocks silently
            continue
            
    # Sort rankings by predicted return descending
    rankings = sorted(rankings, key=lambda val: val['predicted_return'], reverse=True)
    return JSONResponse(content={'success': True, 'rankings': rankings})
