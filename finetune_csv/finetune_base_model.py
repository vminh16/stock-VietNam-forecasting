import os
import sys
import json
import time
import pickle
import random
import glob
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.utils.data.distributed import DistributedSampler
from time import gmtime, strftime
import logging
from logging.handlers import RotatingFileHandler
import datetime
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model import Kronos, KronosTokenizer, KronosPredictor
from config_loader import CustomFinetuneConfig
from training_utils import (
    create_amp_context, 
    amp_backward_step,
    save_checkpoint, 
    load_checkpoint,
    PreTokenizedDataset,
    get_base_kronos_model,
    get_ddp_unwrapped_model
)
from lora_utils import apply_lora, save_lora, merge_and_save_lora_offline


class CustomKlineDataset(Dataset):
    
    def __init__(self, data_path, data_type='train', lookback_window=90, predict_window=10, 
                 clip=5.0, seed=100, train_end_date='2023-01-01', val_end_date='2024-01-01'):
        self.data_path = data_path
        self.data_type = data_type
        self.lookback_window = lookback_window
        self.predict_window = predict_window
        self.window = lookback_window + predict_window + 1
        self.clip = clip
        self.seed = seed
        self.train_end_date = pd.to_datetime(train_end_date)
        self.val_end_date = pd.to_datetime(val_end_date)
        
        self.feature_list = ['open', 'high', 'low', 'close', 'volume', 'amount']
        self.time_feature_list = ['minute', 'hour', 'weekday', 'day', 'month']
        
        self.py_rng = random.Random(seed)
        
        self._load_and_preprocess_multi_stock()
        self._build_global_index_map()
        
        print(f"[{data_type.upper()}] Loaded {len(self.stock_data)} stocks, Total available windows: {len(self.global_index_map)}")
    
    def _load_and_preprocess_multi_stock(self):
        if os.path.isdir(self.data_path):
            csv_files = glob.glob(os.path.join(self.data_path, "*.csv"))
        else:
            csv_files = [self.data_path]
            
        self.stock_data = {}
        
        for fpath in csv_files:
            symbol = os.path.splitext(os.path.basename(fpath))[0]
            df = pd.read_csv(fpath)
            
            df['timestamps'] = pd.to_datetime(df['timestamps'])
            df = df.sort_values('timestamps').reset_index(drop=True)
            
            # Khắc phục C4: Kiểm tra và bổ sung cột amount nếu thiếu
            if 'amount' not in df.columns:
                df['amount'] = df['volume'] * (df['open'] + df['high'] + df['low'] + df['close']) / 4.0
            
            # Cố định giờ giao dịch 09:00
            df['minute'] = 0
            df['hour'] = 9
            df['weekday'] = df['timestamps'].dt.weekday
            df['day'] = df['timestamps'].dt.day
            df['month'] = df['timestamps'].dt.month
            
            self.stock_data[symbol] = df
            
    def _build_global_index_map(self):
        self.global_index_map = []
        gap_buffer = 5
        
        for symbol, df in self.stock_data.items():
            data_len = len(df)
            if data_len < self.window:
                continue
            
            val_start_series = df['timestamps'] >= self.train_end_date
            test_start_series = df['timestamps'] >= self.val_end_date
            
            first_val_idx = df[val_start_series].index[0] if val_start_series.any() else data_len
            first_test_idx = df[test_start_series].index[0] if test_start_series.any() else data_len
            
            for i in range(data_len - self.window + 1):
                target_start_idx = i + self.lookback_window
                target_end_time = df.loc[i + self.window - 1, 'timestamps']
                
                # Khắc phục C1: Tránh chồng lấp mục tiêu giữa Train/Val/Test có Gap Buffer
                if self.data_type == 'train':
                    if target_end_time >= self.train_end_date:
                        continue
                elif self.data_type == 'val':
                    if target_start_idx < first_val_idx + gap_buffer:
                        continue
                    if target_end_time >= self.val_end_date:
                        continue
                elif self.data_type == 'test':
                    if target_start_idx < first_test_idx + gap_buffer:
                        continue
                
                # Bộ lọc NaN: loại bỏ nếu tỷ lệ NaN > 10%
                window_df = df.iloc[i : i + self.window]
                nan_count = window_df[self.feature_list].isnull().sum().sum()
                total_elements = len(window_df) * len(self.feature_list)
                nan_ratio = nan_count / total_elements
                
                if nan_ratio > 0.10:
                    continue
                    
                self.global_index_map.append((symbol, i))
                
    def set_epoch_seed(self, epoch):
        pass
        
    def __len__(self):
        return len(self.global_index_map)
        
    def __getitem__(self, idx):
        if idx >= len(self.global_index_map):
            raise IndexError("Index out of bounds")
            
        symbol, start_idx = self.global_index_map[idx]
        df = self.stock_data[symbol]
        window_df = df.iloc[start_idx : start_idx + self.window].copy()
        
        # Khắc phục C2: Loại bỏ hoàn toàn bfill để tránh rò rỉ dữ liệu nhãn
        if window_df[self.feature_list].isnull().any().any():
            window_df[self.feature_list] = window_df[self.feature_list].ffill().fillna(0.0)
            
        # Khắc phục M4: Tính toán mean/std ở dạng float64 để bảo toàn precision cho giá VN lớn
        x_double = window_df[self.feature_list].values.astype(np.float64)
        x_stamp = window_df[self.time_feature_list].values.astype(np.float32)
        
        # Tính toán mean/std trên cửa sổ lookback để tránh rò rỉ dữ liệu tương lai
        x_lookback = x_double[:self.lookback_window]
        x_mean = np.mean(x_lookback, axis=0)
        x_std = np.std(x_lookback, axis=0)
        x_norm = (x_double - x_mean) / (x_std + 1e-5)
        x_norm = np.clip(x_norm, -self.clip, self.clip).astype(np.float32)
        
        x_tensor = torch.from_numpy(x_norm)
        x_stamp_tensor = torch.from_numpy(x_stamp)
        
        return x_tensor, x_stamp_tensor




def setup_logging(exp_name: str, log_dir: str, rank: int = 0) -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger(f"basemodel_training_rank_{rank}")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
    
    log_file = os.path.join(log_dir, f"basemodel_training_rank_{rank}.log")
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    console_handler = None
    if rank == 0:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    if console_handler is not None:
        console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    if console_handler is not None:
        logger.addHandler(console_handler)
    
    logger.info(f"=== Basemodel Training Started ===")
    logger.info(f"Experiment Name: {exp_name}")
    logger.info(f"Log Directory: {log_dir}")
    logger.info(f"Rank: {rank}")
    logger.info(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return logger


def create_dataloaders(config):
    if not dist.is_available() or not dist.is_initialized() or dist.get_rank() == 0:
        print("Creating data loaders...")
    
    train_end_date = config.loader.get('data.train_end_date', '2023-01-01')
    val_end_date = config.loader.get('data.val_end_date', '2024-01-01')
    
    train_dataset = CustomKlineDataset(
        data_path=config.data_path,
        data_type='train',
        lookback_window=config.lookback_window,
        predict_window=config.predict_window,
        clip=config.clip,
        seed=config.seed,
        train_end_date=train_end_date,
        val_end_date=val_end_date
    )
    
    val_dataset = CustomKlineDataset(
        data_path=config.data_path,
        data_type='val',
        lookback_window=config.lookback_window,
        predict_window=config.predict_window,
        clip=config.clip,
        seed=config.seed + 1,
        train_end_date=train_end_date,
        val_end_date=val_end_date
    )
    
    use_ddp = dist.is_available() and dist.is_initialized()
    train_sampler = DistributedSampler(train_dataset, num_replicas=dist.get_world_size(), rank=dist.get_rank(), shuffle=True) if use_ddp else None
    val_sampler = DistributedSampler(val_dataset, num_replicas=dist.get_world_size(), rank=dist.get_rank(), shuffle=False, drop_last=False) if use_ddp else None

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=(train_sampler is None),
        num_workers=config.num_workers,
        pin_memory=True,
        drop_last=True,
        sampler=train_sampler
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
        drop_last=False,
        sampler=val_sampler
    )
    
    if not dist.is_available() or not dist.is_initialized() or dist.get_rank() == 0:
        print(f"Training set size: {len(train_dataset)}, Validation set size: {len(val_dataset)}")
    
    return train_loader, val_loader, train_dataset, val_dataset, train_sampler, val_sampler


def evaluate_val_directional_accuracy(model, tokenizer, val_dataset, device, config):
    import random
    model.eval()
    tokenizer.eval()
    
    unwrapped_model = get_ddp_unwrapped_model(model)
    # Move tokenizer to device temporarily for prediction
    tokenizer = tokenizer.to(device)
    
    predictor = KronosPredictor(unwrapped_model, tokenizer, device=device, max_context=config.max_context, clip=config.clip)
    
    total_val_windows = len(val_dataset)
    if total_val_windows == 0:
        return 0.0
        
    sample_indices = list(range(total_val_windows))
    if len(sample_indices) > 200:
        # Deterministic sample using fixed seed
        rng = random.Random(42)
        sample_indices = rng.sample(sample_indices, 200)
        
    df_list = []
    x_ts_list = []
    y_ts_list = []
    actual_changes = []
    
    for idx in sample_indices:
        symbol, start_idx = val_dataset.global_index_map[idx]
        df = val_dataset.stock_data[symbol]
        
        lookback_df = df.iloc[start_idx : start_idx + config.lookback_window].copy()
        future_df = df.iloc[start_idx + config.lookback_window : start_idx + config.lookback_window + config.predict_window].copy()
        
        if len(future_df) < config.predict_window:
            continue
            
        current_close = lookback_df.iloc[-1]['close']
        actual_close_5d = future_df.iloc[-1]['close']
        
        df_list.append(lookback_df)
        x_ts_list.append(lookback_df['timestamps'])
        y_ts_list.append(future_df['timestamps'])
        actual_changes.append(actual_close_5d - current_close)
        
    if len(df_list) == 0:
        return 0.0
        
    try:
        # Batch evaluation to prevent Out Of Memory (OOM) on GPU
        eval_batch_size = 16
        pred_dfs = []
        for i in range(0, len(df_list), eval_batch_size):
            batch_dfs = df_list[i : i + eval_batch_size]
            batch_x_ts = x_ts_list[i : i + eval_batch_size]
            batch_y_ts = y_ts_list[i : i + eval_batch_size]
            
            batch_preds = predictor.predict_batch(
                batch_dfs, 
                batch_x_ts, 
                batch_y_ts, 
                pred_len=config.predict_window, 
                sample_count=5, 
                verbose=False
            )
            pred_dfs.extend(batch_preds)
            
        correct_dir = 0
        total_eval = 0
        for i, pred_df in enumerate(pred_dfs):
            current_close = df_list[i].iloc[-1]['close']
            predicted_close_5d = pred_df.iloc[-1]['close']
            predicted_change = predicted_close_5d - current_close
            actual_change = actual_changes[i]
            
            if (actual_change > 0 and predicted_change > 0) or (actual_change <= 0 and predicted_change <= 0):
                correct_dir += 1
            total_eval += 1
            
        # Return tokenizer to CPU if pre_tokenize is enabled to save GPU VRAM
        if getattr(config, 'pre_tokenize', False):
            tokenizer = tokenizer.cpu()
            torch.cuda.empty_cache()
            
        if total_eval > 0:
            return (correct_dir / total_eval) * 100
        else:
            return 0.0
    except Exception as e:
        print(f"Error during validation Directional Accuracy calculation: {str(e)}")
        if getattr(config, 'pre_tokenize', False):
            tokenizer = tokenizer.cpu()
            torch.cuda.empty_cache()
        return 0.0


def train_model(model, tokenizer, device, config, save_dir, logger):
    logger.info("Starting training...")
    use_ddp = dist.is_available() and dist.is_initialized()
    rank = dist.get_rank() if use_ddp else 0
    world_size = dist.get_world_size() if use_ddp else 1
    
    train_loader, val_loader, train_dataset, val_dataset, train_sampler, val_sampler = create_dataloaders(config)
    
    # === Pre-tokenize (nếu enabled) ===
    use_pretokenized = getattr(config, 'pre_tokenize', False)
    if use_pretokenized:
        logger.info("Pre-tokenizing training and validation data...")
        if rank == 0:
            print("Pre-tokenizing training and validation data...")
        
        train_pre_dataset = PreTokenizedDataset(train_dataset, tokenizer, device, batch_size=config.batch_size)
        val_pre_dataset = PreTokenizedDataset(val_dataset, tokenizer, device, batch_size=config.batch_size)
        
        # Giải phóng tokenizer khỏi GPU để tiết kiệm VRAM
        tokenizer = tokenizer.cpu()
        torch.cuda.empty_cache()
        
        # Tạo lại DataLoaders bảo toàn sampler của DDP
        if use_ddp:
            train_sampler = DistributedSampler(train_pre_dataset, num_replicas=dist.get_world_size(), rank=dist.get_rank(), shuffle=True)
            val_sampler = DistributedSampler(val_pre_dataset, num_replicas=dist.get_world_size(), rank=dist.get_rank(), shuffle=False, drop_last=False)

        train_loader = DataLoader(
            train_pre_dataset,
            batch_size=config.batch_size,
            shuffle=(train_sampler is None),
            num_workers=config.num_workers,
            pin_memory=(device.type == 'cuda'),
            drop_last=True,
            sampler=train_sampler
        )
        val_loader = DataLoader(
            val_pre_dataset,
            batch_size=config.batch_size,
            shuffle=False,
            num_workers=config.num_workers,
            pin_memory=(device.type == 'cuda'),
            drop_last=False,
            sampler=val_sampler
        )
    
    # === LoRA (nếu enabled) ===
    use_lora = getattr(config, 'use_lora', False)
    if use_lora:
        model = apply_lora(model, config)
        
    # Trainable parameters list
    trainable_params = [p for p in model.parameters() if p.requires_grad]

    # Optimizer — chỉ tối ưu các tham số trainable
    optimizer = torch.optim.AdamW(
        trainable_params,
        lr=config.predictor_learning_rate,
        betas=(config.adam_beta1, config.adam_beta2),
        weight_decay=config.adam_weight_decay
    )
    
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=config.predictor_learning_rate,
        steps_per_epoch=len(train_loader),
        epochs=config.basemodel_epochs,
        pct_start=0.03,
        div_factor=10
    )
    
    if use_ddp:
        local_rank = int(os.environ.get("LOCAL_RANK", "0"))
        model = DDP(model, device_ids=[local_rank], output_device=local_rank, find_unused_parameters=False)

    # Early stopping & best model tracking parameters
    monitor_metric = getattr(config, 'early_stopping_monitor', 'val_loss')
    monitor_mode = getattr(config, 'early_stopping_mode', 'min')
    patience = getattr(config, 'early_stopping_patience', 5)
    patience_counter = 0
    
    best_val_loss = float('inf')
    if monitor_mode == 'max':
        best_monitor_val = -float('inf')
    else:
        best_monitor_val = float('inf')
        
    batch_idx_global = 0
    start_epoch = 0
    
    # === AMP ===
    amp_enabled, scaler = create_amp_context(device, getattr(config, 'amp_enabled', False))
    
    # === Checkpoint resume ===
    ckpt_path = os.path.join(save_dir, "checkpoint.pt")
    if getattr(config, 'checkpoint_resume', False) and os.path.exists(ckpt_path):
        start_epoch, best_val_loss = load_checkpoint(ckpt_path, model, optimizer, scheduler, scaler, device)
        logger.info(f"Resumed training from epoch {start_epoch} with best_val_loss: {best_val_loss:.4f}")
        if rank == 0:
            print(f"Resumed training from epoch {start_epoch} with best_val_loss: {best_val_loss:.4f}")
        if monitor_metric == 'val_loss':
            best_monitor_val = best_val_loss
        elif monitor_metric == 'val_directional_accuracy':
            if rank == 0:
                logger.info("Evaluating baseline Validation Directional Accuracy for resumed checkpoint...")
                print("Evaluating baseline Validation Directional Accuracy for resumed checkpoint...")
                best_monitor_val = evaluate_val_directional_accuracy(model, tokenizer, val_dataset, device, config)
                logger.info(f"Baseline Validation Directional Accuracy: {best_monitor_val:.2f}%")
                print(f"Baseline Validation Directional Accuracy: {best_monitor_val:.2f}%")

    for epoch in range(start_epoch, config.basemodel_epochs):
        epoch_start_time = time.time()
        model.train()
        
        train_dataset.set_epoch_seed(epoch * 10000)
        val_dataset.set_epoch_seed(0)
        if train_sampler is not None:
            train_sampler.set_epoch(epoch)
        
        epoch_train_loss = 0.0
        train_batches = 0
        
        for batch_idx, batch_data in enumerate(train_loader):
            if use_pretokenized:
                s1_tokens, s2_tokens, batch_x_stamp = batch_data
                s1_tokens = s1_tokens.to(device, non_blocking=True)
                s2_tokens = s2_tokens.to(device, non_blocking=True)
                batch_x_stamp = batch_x_stamp.to(device, non_blocking=True)
                # Cast về int64 (long) để tương thích với Embedding layer
                token_seq_0, token_seq_1 = s1_tokens.long(), s2_tokens.long()
            else:
                batch_x, batch_x_stamp = batch_data
                batch_x = batch_x.to(device, non_blocking=True)
                batch_x_stamp = batch_x_stamp.to(device, non_blocking=True)
                
                with torch.no_grad():
                    with torch.amp.autocast('cuda', enabled=amp_enabled):
                        token_seq_0, token_seq_1 = tokenizer.encode(batch_x, half=True)
            
            token_in = [token_seq_0[:, :-1], token_seq_1[:, :-1]]
            token_out = [token_seq_0[:, 1:], token_seq_1[:, 1:]]
            
            optimizer.zero_grad()
            with torch.amp.autocast('cuda', enabled=amp_enabled):
                logits = model(token_in[0], token_in[1], batch_x_stamp[:, :-1, :])
                base_kronos = get_base_kronos_model(model)
                loss, s1_loss, s2_loss = base_kronos.head.compute_loss(logits[0], logits[1], token_out[0], token_out[1])
            
            # Khắc phục lỗi NaN/Inf Loss theo torch-training-guard
            if torch.isnan(loss) or torch.isinf(loss):
                raise RuntimeError(f"NaN/Inf loss encountered at Epoch {epoch+1}, Step {batch_idx+1}.")
                
            amp_backward_step(scaler, loss, optimizer, trainable_params, max_norm=1.0)
            scheduler.step()
            
            epoch_train_loss += loss.item()
            train_batches += 1
            
            if (batch_idx_global + 1) % config.log_interval == 0:
                # Tính tổng gradient norm để giám sát ổn định số học
                total_grad_norm = sum(p.grad.norm().item() ** 2 for p in trainable_params if p.grad is not None) ** 0.5
                lr = optimizer.param_groups[0]['lr']
                log_msg = (f"[Epoch {epoch+1}/{config.basemodel_epochs}, Step {batch_idx+1}/{len(train_loader)}] "
                          f"LR: {lr:.6f}, Loss: {loss.item():.4f}, Grad Norm: {total_grad_norm:.4f}")
                logger.info(log_msg)
                if rank == 0:
                    print(log_msg)
                if total_grad_norm > 100.0:
                    logger.warning(f"Gradient explosion warning: norm={total_grad_norm:.4f} at global step {batch_idx_global+1}")
            
            batch_idx_global += 1
        
        model.eval()
        val_loss = 0.0
        val_batches = 0
        
        with torch.no_grad():
            for batch_data in val_loader:
                if use_pretokenized:
                    s1_tokens, s2_tokens, batch_x_stamp = batch_data
                    s1_tokens = s1_tokens.to(device, non_blocking=True)
                    s2_tokens = s2_tokens.to(device, non_blocking=True)
                    batch_x_stamp = batch_x_stamp.to(device, non_blocking=True)
                    token_seq_0, token_seq_1 = s1_tokens.long(), s2_tokens.long()
                else:
                    batch_x, batch_x_stamp = batch_data
                    batch_x = batch_x.to(device, non_blocking=True)
                    batch_x_stamp = batch_x_stamp.to(device, non_blocking=True)
                    with torch.amp.autocast('cuda', enabled=amp_enabled):
                        token_seq_0, token_seq_1 = tokenizer.encode(batch_x, half=True)
                
                token_in = [token_seq_0[:, :-1], token_seq_1[:, :-1]]
                token_out = [token_seq_0[:, 1:], token_seq_1[:, 1:]]
                
                with torch.amp.autocast('cuda', enabled=amp_enabled):
                    logits = model(token_in[0], token_in[1], batch_x_stamp[:, :-1, :])
                    base_kronos = get_base_kronos_model(model)
                    loss, _, _ = base_kronos.head.compute_loss(logits[0], logits[1], token_out[0], token_out[1])
                
                val_loss += loss.item()
                val_batches += 1
        
        if use_ddp:
            tensor_sum = torch.tensor([epoch_train_loss, train_batches, val_loss, val_batches], dtype=torch.float64, device=device)
            dist.all_reduce(tensor_sum, op=dist.ReduceOp.SUM)
            epoch_train_loss_all = tensor_sum[0].item()
            train_batches_all = int(tensor_sum[1].item())
            val_loss_all = tensor_sum[2].item()
            val_batches_all = int(tensor_sum[3].item())
            avg_train_loss = (epoch_train_loss_all / train_batches_all) if train_batches_all > 0 else 0.0
            avg_val_loss = (val_loss_all / val_batches_all) if val_batches_all > 0 else 0.0
        else:
            avg_train_loss = epoch_train_loss / train_batches if train_batches > 0 else 0
            avg_val_loss = val_loss / val_batches if val_batches > 0 else 0
        
        # Evaluate validation Directional Accuracy (DA)
        val_da = 0.0
        if rank == 0:
            val_da = evaluate_val_directional_accuracy(model, tokenizer, val_dataset, device, config)
            
        epoch_time = time.time() - epoch_start_time
        epoch_summary = (f"\n--- Epoch {epoch+1}/{config.basemodel_epochs} Summary ---\n"
                       f"Training Loss: {avg_train_loss:.4f}\n"
                       f"Validation Loss: {avg_val_loss:.4f}\n"
                       f"Validation Directional Accuracy: {val_da:.2f}%\n"
                       f"Epoch Time: {epoch_time:.2f} seconds\n")
        logger.info(epoch_summary)
        if rank == 0:
            print(epoch_summary)
            
        # === Lưu checkpoint định kỳ ===
        checkpoint_interval = getattr(config, 'checkpoint_interval', 1)
        if rank == 0 and (epoch + 1) % checkpoint_interval == 0:
            save_checkpoint(ckpt_path, model, optimizer, scheduler, scaler, epoch, best_val_loss)
        
        # Check early stopping and save best model (rank 0 decides, others receive signal)
        stop_training = torch.tensor(0, dtype=torch.int32, device=device)
        
        if rank == 0:
            current_monitor_val = val_da if monitor_metric == 'val_directional_accuracy' else avg_val_loss
            
            improved = False
            if monitor_mode == 'max':
                if current_monitor_val > best_monitor_val:
                    best_monitor_val = current_monitor_val
                    improved = True
            else:
                if current_monitor_val < best_monitor_val:
                    best_monitor_val = current_monitor_val
                    improved = True
                    
            if improved:
                patience_counter = 0
                best_val_loss = avg_val_loss # Maintain best_val_loss for checkpoint compatibility
                
                model_save_path = os.path.join(save_dir, "best_model")
                os.makedirs(model_save_path, exist_ok=True)
                
                unwrapped_model = get_ddp_unwrapped_model(model)
                if use_lora:
                    adapter_path = os.path.join(save_dir, "best_lora")
                    save_lora(unwrapped_model, adapter_path)
                    save_msg = f"Best adapter saved to: {adapter_path} ({monitor_metric}: {best_monitor_val:.4f})"
                else:
                    unwrapped_model.save_pretrained(model_save_path)
                    save_msg = f"Best model saved to: {model_save_path} ({monitor_metric}: {best_monitor_val:.4f})"
                    
                logger.info(save_msg)
                print(save_msg)
            else:
                patience_counter += 1
                logger.info(f"Early stopping patience counter: {patience_counter}/{patience}")
                print(f"Early stopping patience counter: {patience_counter}/{patience}")
                if patience_counter >= patience:
                    stop_training.fill_(1)
                    
        # Broadcast early stopping signal in case of DDP
        if use_ddp:
            dist.broadcast(stop_training, src=0)
            
        if stop_training.item() == 1:
            if rank == 0:
                logger.info(f"Early stopping triggered at Epoch {epoch+1}.")
                print(f"Early stopping triggered at Epoch {epoch+1}.")
            break
                
    # === Gộp trọng số LoRA ngoại tuyến (chỉ thực hiện 1 lần duy nhất ở cuối) ===
    if rank == 0 and use_lora:
        adapter_path = os.path.join(save_dir, "best_lora")
        model_save_path = os.path.join(save_dir, "best_model")
        if os.path.exists(adapter_path):
            merge_msg = f"Starting final offline merge of LoRA weights to: {model_save_path}..."
            logger.info(merge_msg)
            print(merge_msg)
            merge_and_save_lora_offline(
                base_model_path=config.pretrained_predictor_path,
                adapter_path=adapter_path,
                output_path=model_save_path
            )
            logger.info("Final offline merge completed successfully!")
            print("Final offline merge completed successfully!")
    
    return best_val_loss


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Kronos Basemodel Fine-tuning Training')
    parser.add_argument('--config', type=str, default='config.yaml', 
                       help='Configuration file path (default: config.yaml)')
    args = parser.parse_args()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    config = CustomFinetuneConfig(args.config)
    
    os.makedirs(config.basemodel_save_path, exist_ok=True)
    
    log_dir = os.path.join(config.base_save_path, "logs")
    logger = setup_logging(config.exp_name, log_dir, 0)
    
    torch.manual_seed(config.seed)
    np.random.seed(config.seed)
    random.seed(config.seed)
    
    logger.info("Loading pretrained model or random initialization...")
    print("Loading pretrained model or random initialization...")
    if getattr(config, 'pre_trained_tokenizer', True):
        tokenizer = KronosTokenizer.from_pretrained(config.finetuned_tokenizer_path)
    else:
        import json
        print("pre_trained_tokenizer=False, randomly initializing Tokenizer architecture for training")
        cfg_path_tok = os.path.join(config.pretrained_tokenizer_path if hasattr(config, 'pretrained_tokenizer_path') else config.finetuned_tokenizer_path, 'config.json')
        with open(cfg_path_tok, 'r') as f:
            arch_t = json.load(f)
        tokenizer = KronosTokenizer(
            d_in=arch_t.get('d_in', 6),
            d_model=arch_t.get('d_model', 256),
            n_heads=arch_t.get('n_heads', 4),
            ff_dim=arch_t.get('ff_dim', 512),
            n_enc_layers=arch_t.get('n_enc_layers', 4),
            n_dec_layers=arch_t.get('n_dec_layers', 4),
            ffn_dropout_p=arch_t.get('ffn_dropout_p', 0.0),
            attn_dropout_p=arch_t.get('attn_dropout_p', 0.0),
            resid_dropout_p=arch_t.get('resid_dropout_p', 0.0),
            s1_bits=arch_t.get('s1_bits', 10),
            s2_bits=arch_t.get('s2_bits', 10),
            beta=arch_t.get('beta', 0.05),
            gamma0=arch_t.get('gamma0', 1.0),
            gamma=arch_t.get('gamma', 1.1),
            zeta=arch_t.get('zeta', 0.05),
            group_size=arch_t.get('group_size', 4)
        )

    if getattr(config, 'pre_trained_predictor', True):
        model = Kronos.from_pretrained(config.pretrained_predictor_path)
    else:
        import json
        print("pre_trained_predictor=False, randomly initializing Predictor architecture for training")
        cfg_path = os.path.join(config.pretrained_predictor_path, 'config.json')
        with open(cfg_path, 'r') as f:
            arch = json.load(f)
        model = Kronos(
            s1_bits=arch.get('s1_bits', 10),
            s2_bits=arch.get('s2_bits', 10),
            n_layers=arch.get('n_layers', 12),
            d_model=arch.get('d_model', 832),
            n_heads=arch.get('n_heads', 16),
            ff_dim=arch.get('ff_dim', 2048),
            ffn_dropout_p=arch.get('ffn_dropout_p', 0.2),
            attn_dropout_p=arch.get('attn_dropout_p', 0.0),
            resid_dropout_p=arch.get('resid_dropout_p', 0.2),
            token_dropout_p=arch.get('token_dropout_p', 0.0),
            learn_te=arch.get('learn_te', True)
        )
    
    tokenizer = tokenizer.to(device)
    model = model.to(device)
    
    model_size = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {model_size:,}")
    print(f"Model parameters: {model_size:,}")
    
    logger.info("=== Training Configuration ===")
    logger.info(f"Data path: {config.data_path}")
    logger.info(f"Lookback window: {config.lookback_window}")
    logger.info(f"Predict window: {config.predict_window}")
    logger.info(f"Batch size: {config.batch_size}")
    logger.info(f"Learning rate: {config.predictor_learning_rate}")
    logger.info(f"Training epochs: {config.basemodel_epochs}")
    logger.info(f"Device: {device}")
    logger.info(f"Tokenizer path: {config.finetuned_tokenizer_path}")
    logger.info(f"Pretrained model path: {config.pretrained_predictor_path}")
    
    logger.info("Starting fine-tuning training...")
    print("Starting fine-tuning training...")
    best_val_loss = train_model(model, tokenizer, device, config, config.basemodel_save_path, logger)
    
    final_msg = f"Training completed! Best validation loss: {best_val_loss:.4f}\nModel saved to: {config.basemodel_save_path}"
    logger.info(final_msg)
    print(final_msg)


if __name__ == "__main__":
    main()
