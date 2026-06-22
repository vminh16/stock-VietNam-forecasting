import os
import yaml
import glob
import datetime
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from model import Kronos, KronosTokenizer, KronosPredictor
from model.kronos import calc_time_stamps, sample_from_logits

# Static Stock Metadata
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


class KronosInferencePipeline:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        
        self.tokenizer_model = None
        self.predictor_model = None
        self.predictor = None
        self.device = self.config.get('device', 'cpu')
        
    def _load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
            
    def load_model(self, model_id_path: str, tokenizer_id_path: str, device_name: str):
        # Resolve CUDA availability
        if device_name.startswith("cuda") and not torch.cuda.is_available():
            device_name = "cpu"
        self.device = device_name
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Helper to convert paths if relative
        def resolve_path(p):
            if not os.path.isabs(p):
                return os.path.join(project_root, p)
            return p
            
        t_path = resolve_path(tokenizer_id_path)
        p_path = resolve_path(model_id_path)
        
        if not os.path.exists(t_path):
            raise FileNotFoundError(f"Tokenizer path does not exist: {t_path}")
        if not os.path.exists(p_path):
            raise FileNotFoundError(f"Predictor path does not exist: {p_path}")
            
        self.tokenizer_model = KronosTokenizer.from_pretrained(t_path).to(self.device)
        self.predictor_model = Kronos.from_pretrained(p_path).to(self.device)
        self.tokenizer_model.eval()
        self.predictor_model.eval()
        
        self.predictor = KronosPredictor(
            self.predictor_model, 
            self.tokenizer_model, 
            device=self.device, 
            max_context=self.config.get('max_context', 512), 
            clip=self.config.get('clip', 5.0)
        )
        
    def load_data_file(self, file_path: str):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not os.path.isabs(file_path):
            clean_path = file_path
            if clean_path.startswith('./') or clean_path.startswith('.\\'):
                clean_path = clean_path[2:]
            file_path = os.path.join(project_root, clean_path)
            
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
            
    def predict(
        self,
        symbol: str,
        lookback: int = 126,
        pred_len: int = 5,
        temperature: float = 1.0,
        top_p: float = 0.9,
        sample_count: int = 50,
        start_date: str = None
    ):
        if self.tokenizer_model is None or self.predictor_model is None or self.predictor is None:
            raise RuntimeError("Mô hình chưa được nạp. Vui lòng nạp mô hình trước khi dự báo.")
            
        # Resolve path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Check canonical data cleaner directory first
        fpath = None
        for data_dir in ["data_cleaned", "data"]:
            check_path = os.path.join(project_root, data_dir, f"{symbol.upper()}.csv")
            if os.path.exists(check_path):
                fpath = check_path
                break
                
        if fpath is None:
            raise ValueError(f"Không tìm thấy dữ liệu cho mã {symbol}")
            
        df, err = self.load_data_file(fpath)
        if err:
            raise ValueError(err)
            
        if len(df) < lookback:
            raise ValueError(f"Dữ liệu lịch sử không đủ, cần tối thiểu {lookback} nến.")
            
        # Slicing context window
        if start_date:
            start_dt = pd.to_datetime(start_date)
            mask = df['timestamps'] >= start_dt
            time_range_df = df[mask]
            
            if len(time_range_df) < lookback:
                raise ValueError(f"Không đủ {lookback} nến lịch sử tính từ ngày {start_date}")
                
            x_df = time_range_df.iloc[:lookback]
            
            # Check if actual comparison candles are available in the CSV
            if len(time_range_df) >= lookback + pred_len:
                actual_df = time_range_df.iloc[lookback:lookback+pred_len]
                has_comparison = True
            else:
                actual_df = pd.DataFrame()
                has_comparison = False
        else:
            # Default behavior: shift back by 7 days to allow visual comparison with ground truth
            if len(df) >= lookback + 7:
                x_df = df.iloc[-(lookback + 7):-7]
                actual_df = df.iloc[-7:-7+pred_len]
                has_comparison = True
            else:
                # Fallback to the latest available dataset rows, no ground truth comparison
                x_df = df.iloc[-lookback:]
                actual_df = pd.DataFrame()
                has_comparison = False
                
        price_cols = ['open', 'high', 'low', 'close']
        features = price_cols + ['volume', 'amount']
        x_raw = x_df[features].values.astype(np.float64)
        x_timestamps = x_df['timestamps'].reset_index(drop=True)
        
        if has_comparison:
            y_timestamps = actual_df['timestamps'].reset_index(drop=True)
        else:
            # Generate future timestamps (business days approx)
            if len(x_timestamps) > 1:
                time_diff = x_timestamps.iloc[-1] - x_timestamps.iloc[-2]
            else:
                time_diff = pd.Timedelta(days=1)
                
            y_timestamps = []
            curr_time = x_timestamps.iloc[-1]
            for _ in range(pred_len):
                curr_time += time_diff
                y_timestamps.append(curr_time)
            y_timestamps = pd.Series(y_timestamps)
            
        x_mean = np.mean(x_raw, axis=0)
        x_std = np.std(x_raw, axis=0)
        x_std = np.where(x_std < 1e-6, 1.0, x_std)
        x_norm = (x_raw - x_mean) / (x_std + 1e-5)
        x_norm = np.clip(x_norm, -self.predictor.clip, self.predictor.clip)
        
        x_tensor = torch.from_numpy(x_norm[np.newaxis, ...].astype(np.float32)).to(self.device)
        x_stamp_df = calc_time_stamps(pd.Series(x_timestamps))
        y_stamp_df = calc_time_stamps(pd.Series(y_timestamps))
        
        x_stamp_tensor = torch.from_numpy(x_stamp_df.values[np.newaxis, ...].astype(np.float32)).to(self.device)
        y_stamp_tensor = torch.from_numpy(y_stamp_df.values[np.newaxis, ...].astype(np.float32)).to(self.device)
        
        paths_norm = auto_regressive_inference_paths(
            self.tokenizer_model, self.predictor_model, x_tensor, x_stamp_tensor, y_stamp_tensor,
            max_context=self.predictor.max_context, pred_len=pred_len, clip=self.predictor.clip,
            T=temperature, top_p=top_p, sample_count=sample_count
        )
        paths_norm = paths_norm.squeeze(0)
        pred_paths_norm = paths_norm[:, -pred_len:, :]
        pred_paths_raw = pred_paths_norm * (x_std + 1e-5) + x_mean
        mean_pred_raw = np.mean(pred_paths_raw, axis=0)
        
        full_df_raw = np.concatenate([x_raw, mean_pred_raw], axis=0)
        full_norm = (full_df_raw - x_mean) / (x_std + 1e-5)
        full_norm = np.clip(full_norm, -self.predictor.clip, self.predictor.clip)
        full_tensor = torch.from_numpy(full_norm[np.newaxis, ...].astype(np.float32)).to(self.device)
        
        with torch.no_grad():
            z_indices = self.tokenizer_model.encode(full_tensor, half=True)
            s1_tokens = z_indices[0].squeeze(0).cpu().numpy()
            
        last_s1 = s1_tokens[-15:].tolist()
        unique, counts = np.unique(last_s1, return_counts=True)
        xai_data = [{'token': int(t), 'frequency': int(c)} for t, c in zip(unique, counts)]
        xai_data = sorted(xai_data, key=lambda val: val['frequency'], reverse=True)
        
        close_samples = pred_paths_raw[:, -1, 3]
        volatility = float(np.std(close_samples) / np.mean(close_samples))
        var_5pct = float(np.percentile(close_samples, 5))
        var_95pct = float(np.percentile(close_samples, 95))
        confidence_width = float(var_95pct - var_5pct)
        
        current_close = float(x_df.iloc[-1]['close'])
        pred_close_5d = float(mean_pred_raw[-1, 3])
        predicted_return = (pred_close_5d - current_close) / current_close
        
        trend_class = "SIDEWAY"
        if predicted_return > 0.03:
            trend_class = "UP"
        elif predicted_return < -0.03:
            trend_class = "DOWN"
            
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
        for i in range(pred_len):
            prediction_results.append({
                'timestamp': y_timestamps[i].isoformat(),
                'open': float(mean_pred_raw[i, 0]),
                'high': float(mean_pred_raw[i, 1]),
                'low': float(mean_pred_raw[i, 2]),
                'close': float(mean_pred_raw[i, 3]),
                'volume': float(mean_pred_raw[i, 4]),
                'amount': float(mean_pred_raw[i, 5])
            })
            
        total_candles = raw_candles + prediction_results
        
        stochastic_paths = []
        for p_idx in range(sample_count):
            path_candles = []
            for i in range(pred_len):
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
                
        meta = STOCK_METADATA.get(symbol, {"name": symbol, "sector": "Khác", "exchange": symbol})
        
        return {
            'success': True,
            'symbol': symbol,
            'name': meta['name'],
            'sector': meta['sector'],
            'exchange': meta['exchange'],
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
        }
