"""Training utilities: AMP, checkpoint, pre-tokenize."""
import os
import torch
from torch.utils.data import Dataset, DataLoader

# ============================================================
# 1. Model Unwrapping Helpers
# ============================================================
def get_ddp_unwrapped_model(model):
    """Unwrap DDP wrapper if present."""
    if hasattr(model, 'module'):
        return model.module
    return model


def get_base_kronos_model(model):
    """Unwrap DDP and PEFT layers to get raw Kronos model."""
    m = model
    if hasattr(m, 'module'):        # Unwrap DDP
        m = m.module
    if hasattr(m, 'get_base_model'): # Unwrap PEFT
        m = m.get_base_model()
    return m

# ============================================================
# 2. AMP Helper
# ============================================================
def create_amp_context(device, enabled=True):
    """Returns (amp_enabled (bool), GradScaler)."""
    amp_enabled = enabled and (device.type == 'cuda')
    scaler = torch.amp.GradScaler('cuda') if amp_enabled else None
    return amp_enabled, scaler


def amp_backward_step(scaler, loss, optimizer, model_params, max_norm=1.0):
    """AMP-aware backward step with gradient scaling and clipping."""
    if scaler is not None:
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model_params, max_norm=max_norm)
        scaler.step(optimizer)
        scaler.update()
    else:
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model_params, max_norm=max_norm)
        optimizer.step()

# ============================================================
# 3. Checkpoint Save/Resume
# ============================================================
def save_checkpoint(path, model, optimizer, scheduler, scaler, epoch, best_val_loss):
    """Save full training state, unwrapping DDP."""
    unwrapped = get_ddp_unwrapped_model(model)
    state = {
        'epoch': epoch,
        'best_val_loss': best_val_loss,
        'model_state_dict': unwrapped.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
    }
    if scaler is not None:
        state['scaler_state_dict'] = scaler.state_dict()
    torch.save(state, path)


def load_checkpoint(path, model, optimizer, scheduler, scaler=None, device=None):
    """Load checkpoint state into unwrapped model and device-aligned optimizer."""
    if not os.path.exists(path):
        return 0, float('inf')
    
    ckpt = torch.load(path, map_location='cpu', weights_only=False)
    
    unwrapped = get_ddp_unwrapped_model(model)
    unwrapped.load_state_dict(ckpt['model_state_dict'])
    
    optimizer.load_state_dict(ckpt['optimizer_state_dict'])
    scheduler.load_state_dict(ckpt['scheduler_state_dict'])
    
    # Align optimizer state tensors to device to prevent device mismatch errors
    if device is not None:
        for state in optimizer.state.values():
            for k, v in state.items():
                if isinstance(v, torch.Tensor):
                    state[k] = v.to(device)
                    
    if scaler is not None and 'scaler_state_dict' in ckpt:
        scaler.load_state_dict(ckpt['scaler_state_dict'])
        
    return ckpt['epoch'] + 1, ckpt['best_val_loss']

# ============================================================
# 4. Pre-tokenize Dataset
# ============================================================
class PreTokenizedDataset(Dataset):
    """Dataset storing pre-computed tokens in CPU RAM using int32 optimization."""

    def __init__(self, raw_dataset, tokenizer, device, batch_size=64):
        self.stamps = []
        self.s1_tokens = []
        self.s2_tokens = []

        tokenizer.eval()
        loader = DataLoader(
            raw_dataset, 
            batch_size=batch_size, 
            shuffle=False, 
            num_workers=0, 
            pin_memory=(device.type == 'cuda')
        )

        import time
        start_time = time.time()
        total_batches = len(loader)

        with torch.no_grad():
            for idx, (batch_x, batch_stamp) in enumerate(loader):
                batch_x = batch_x.to(device)
                s1, s2 = tokenizer.encode(batch_x, half=True)
                # Store as int32 to save 50% CPU memory
                self.s1_tokens.append(s1.cpu().to(torch.int32))
                self.s2_tokens.append(s2.cpu().to(torch.int32))
                self.stamps.append(batch_stamp)
                
                if (idx + 1) % 200 == 0 or (idx + 1) == total_batches:
                    elapsed = time.time() - start_time
                    percent = (idx + 1) / total_batches * 100
                    print(f"  [Pre-tokenize] Progress: {idx+1}/{total_batches} batches ({percent:.1f}%) - Elapsed: {elapsed:.1f}s")

        self.s1_tokens = torch.cat(self.s1_tokens, dim=0)
        self.s2_tokens = torch.cat(self.s2_tokens, dim=0)
        self.stamps = torch.cat(self.stamps, dim=0)

    def __len__(self):
        return len(self.s1_tokens)

    def __getitem__(self, idx):
        # Cast back to long (int64) for compatibility with embedding layer
        return self.s1_tokens[idx].long(), self.s2_tokens[idx].long(), self.stamps[idx]
