import base64
import io
import os

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import torch
import torch.nn as nn
import torch.nn.functional as F

CACHE_DIR = "cache_frpinput_seq1_sp128_trimmed"
IMAGE_DIR = "Images"
MODEL_PATH = os.path.join("models", "deepfire_frpinput_best.pt")

SPATIAL_SIZE = 128
FIRE_PEAK = 1.0
FIRE_SIGMA = 5.0
VEGETATION_CLASSES = {5, 7, 11}
OVERLAY_THRESHOLD_HIGH = 0.6
OVERLAY_THRESHOLD_MED = 0.3
IGNITION_THRESHOLD = 0.5
OVERLAY_OPACITY = 0.69


def _load_mask(mask_data_url):
    if not mask_data_url:
        return np.zeros((SPATIAL_SIZE, SPATIAL_SIZE), dtype=np.float32)

    if "," in mask_data_url:
        _, encoded = mask_data_url.split(",", 1)
    else:
        encoded = mask_data_url

    mask_bytes = base64.b64decode(encoded)
    mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L")
    mask_img = mask_img.resize((SPATIAL_SIZE, SPATIAL_SIZE), Image.NEAREST)
    mask_np = np.asarray(mask_img, dtype=np.float32) / 255.0

    if mask_np.max() > 0:
        mask_np = gaussian_filter(mask_np, sigma=FIRE_SIGMA)
        mask_np = mask_np / max(mask_np.max(), 1e-6) * FIRE_PEAK

    return mask_np


def _load_satellite(image_name):
    image_path = os.path.join(IMAGE_DIR, image_name)
    if not os.path.exists(image_path):
        return Image.new("RGB", (SPATIAL_SIZE, SPATIAL_SIZE), (64, 64, 64))

    image = Image.open(image_path).convert("RGB")
    return image


class ConvBNReLU(nn.Module):
    def __init__(self, in_ch, out_ch, kernel=3, stride=1, padding=1):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel, stride=stride, padding=padding, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class ResidualCNNBlock(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(ConvBNReLU(in_ch, out_ch), ConvBNReLU(out_ch, out_ch))
        self.skip = nn.Conv2d(in_ch, out_ch, 1, bias=False) if in_ch != out_ch else nn.Identity()

    def forward(self, x):
        return F.relu(self.conv(x) + self.skip(x), inplace=True)


class SpatialEncoder(nn.Module):
    def __init__(self, viirs_channels, lulc_embed_dim, embed_dim):
        super().__init__()
        in_ch = viirs_channels + lulc_embed_dim
        self.enc1 = ResidualCNNBlock(in_ch, 32)
        self.pool1 = nn.MaxPool2d(2, 2)
        self.enc2 = ResidualCNNBlock(32, 64)
        self.pool2 = nn.MaxPool2d(2, 2)
        self.enc3 = ResidualCNNBlock(64, embed_dim)
        self.pool3 = nn.MaxPool2d(2, 2)

    def forward(self, x):
        s1 = self.enc1(x)
        s2 = self.enc2(self.pool1(s1))
        s3 = self.enc3(self.pool2(s2))
        return s1, s2, s3, self.pool3(s3)


class SpatiotemporalTransformer(nn.Module):
    def __init__(self, embed_dim, num_heads, num_layers, seq_len, spatial_size, dropout):
        super().__init__()
        h = spatial_size // 8
        n = h * h
        self.spatial_pos = nn.Parameter(torch.randn(1, 1, n, embed_dim) * 0.02)
        self.temporal_pos = nn.Parameter(torch.randn(1, seq_len, 1, embed_dim) * 0.02)
        layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers)
        self.norm = nn.LayerNorm(embed_dim)

    def forward(self, x):
        b, t, d, h, w = x.shape
        x = x.view(b, t, d, h * w).permute(0, 1, 3, 2)
        x = x + self.spatial_pos + self.temporal_pos
        x = self.norm(self.transformer(x.reshape(b, t * h * w, d)))
        return x.view(b, t, h * w, d).permute(0, 1, 3, 2).contiguous().view(b, t, d, h, w)


class TemporalAttentionPooling(nn.Module):
    def __init__(self, embed_dim):
        super().__init__()
        self.score_net = nn.Sequential(
            nn.Conv2d(embed_dim, embed_dim // 2, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(embed_dim // 2, 1, 1),
        )

    def forward(self, x):
        b, t, d, h, w = x.shape
        wts = F.softmax(self.score_net(x.view(b * t, d, h, w)).view(b, t, h * w).mean(2), dim=1)
        return (x * wts.view(b, t, 1, 1, 1)).sum(1), wts


class UNetDecoder(nn.Module):
    def __init__(self, embed_dim=128):
        super().__init__()
        self.up3 = nn.Sequential(
            nn.ConvTranspose2d(embed_dim, 64, 4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
        )
        self.refine3 = ResidualCNNBlock(64 + embed_dim, 64)
        self.up2 = nn.Sequential(
            nn.ConvTranspose2d(64, 32, 4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
        )
        self.refine2 = ResidualCNNBlock(32 + 64, 32)
        self.up1 = nn.Sequential(
            nn.ConvTranspose2d(32, 16, 4, stride=2, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
        )
        self.refine1 = ResidualCNNBlock(16 + 32, 16)
        self.head = nn.Conv2d(16, 1, 1)

    def forward(self, bt, s3, s2, s1):
        x = self.refine3(torch.cat([self.up3(bt), s3], 1))
        x = self.refine2(torch.cat([self.up2(x), s2], 1))
        x = self.refine1(torch.cat([self.up1(x), s1], 1))
        return torch.sigmoid(self.head(x))


class DeepFireForecaster(nn.Module):
    def __init__(self, viirs_channels=4, lulc_classes=12, lulc_embed_dim=8, embed_dim=128, num_heads=4, num_layers=3, seq_len=1, spatial_size=128, dropout=0.1):
        super().__init__()
        self.seq_len = seq_len
        self.lulc_embed = nn.Embedding(lulc_classes, lulc_embed_dim)
        self.spatial_encoder = SpatialEncoder(viirs_channels, lulc_embed_dim, embed_dim)
        self.transformer = SpatiotemporalTransformer(embed_dim, num_heads, num_layers, seq_len, spatial_size, dropout)
        self.temporal_pool = TemporalAttentionPooling(embed_dim)
        self.decoder = UNetDecoder(embed_dim)

    def forward(self, viirs, lulc):
        b, t, c, h, w = viirs.shape
        lulc_emb = self.lulc_embed(lulc).permute(0, 3, 1, 2)
        lulc_rep = lulc_emb.unsqueeze(1).expand(-1, t, -1, -1, -1)
        x_in = torch.cat([viirs.view(b * t, c, h, w), lulc_rep.reshape(b * t, 8, h, w)], dim=1)
        s1, s2, s3, bt = self.spatial_encoder(x_in)
        _, d, hb, wb = bt.shape
        bt_seq = self.transformer(bt.view(b, t, d, hb, wb))
        pooled, _ = self.temporal_pool(bt_seq)
        s3_agg = s3.view(b, t, s3.shape[1], *s3.shape[2:]).mean(1)
        s2_agg = s2.view(b, t, s2.shape[1], *s2.shape[2:]).mean(1)
        s1_agg = s1.view(b, t, s1.shape[1], *s1.shape[2:]).mean(1)
        return self.decoder(pooled, s3_agg, s2_agg, s1_agg)


class DeepFirePredictor:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.viirs_channels = 4
        self._load_model()

    def _load_model(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

        checkpoint = torch.load(MODEL_PATH, map_location=self.device)
        enc_weight = checkpoint["model"]["spatial_encoder.enc1.conv.0.block.0.weight"]
        self.viirs_channels = enc_weight.shape[1] - 8
        model = DeepFireForecaster(viirs_channels=self.viirs_channels).to(self.device)
        model.load_state_dict(checkpoint["model"])
        model.eval()
        self.model = model

    def _load_cached_sample(self, image_base):
        for seq in (0, 1):
            cache_file = os.path.join(CACHE_DIR, f"{image_base}_seq{seq:03d}.pt")
            if os.path.exists(cache_file):
                try:
                    sample = torch.load(cache_file, weights_only=True)
                except TypeError:
                    sample = torch.load(cache_file)
                return sample
        raise FileNotFoundError(f"No cached .pt file found for {image_base} in {CACHE_DIR}")

    def _predict(self, viirs, lulc):
        viirs_t = torch.tensor(viirs).unsqueeze(0).unsqueeze(0).to(self.device)
        lulc_t = lulc.unsqueeze(0).to(self.device)
        with torch.no_grad():
            pred_t = self.model(viirs_t, lulc_t)
        return pred_t.squeeze().cpu().numpy()

    def predict_overlay(self, image_name, mask_data_url):
        image_base = os.path.splitext(image_name)[0]
        sample = self._load_cached_sample(image_base)
        viirs_np = sample["viirs"].squeeze(0).numpy()
        lulc_t = sample["lulc"]
        lulc_np = lulc_t.cpu().numpy() if hasattr(lulc_t, "cpu") else np.array(lulc_t)

        mask_np = _load_mask(mask_data_url)

        if viirs_np.shape[0] > 3:
            viirs_np[3] = mask_np
        else:
            viirs_np[-1] = mask_np

        pred_np = self._predict(viirs_np, lulc_t)
        pred_np = np.clip(pred_np, 0, 1)

        vegetation_mask = np.isin(lulc_np, list(VEGETATION_CLASSES)).astype(np.float32)
        if vegetation_mask.max() > 0:
            pred_np = pred_np * vegetation_mask

        base_image = _load_satellite(image_name)
        base_size = base_image.size

        def resize_binary(mask_2d):
            img = Image.fromarray((mask_2d * 255).astype(np.uint8)).resize(base_size, Image.BILINEAR)
            return (np.asarray(img, dtype=np.float32) / 255.0 >= 0.5).astype(np.float32)

        # Three-tier zones: ignition (red) > high spread (orange) > medium spread (yellow)
        ignition = resize_binary((mask_np >= IGNITION_THRESHOLD).astype(np.float32))
        high = resize_binary((pred_np >= OVERLAY_THRESHOLD_HIGH).astype(np.float32))
        med = resize_binary(((pred_np >= OVERLAY_THRESHOLD_MED) & (pred_np < OVERLAY_THRESHOLD_HIGH)).astype(np.float32))

        # Each zone excludes higher-priority zones so colors don't bleed
        high = high * (1 - ignition)
        med = med * (1 - ignition) * (1 - high)

        base_arr = np.asarray(base_image, dtype=np.float32) / 255.0
        overlay = base_arr.copy()

        # Yellow: medium spread (0.4–0.6)
        a = (med * OVERLAY_OPACITY)[..., None]
        overlay = overlay * (1 - a) + np.array([1.0, 0.88, 0.0]) * a

        # Orange: high spread (>= 0.6)
        a = (high * OVERLAY_OPACITY)[..., None]
        overlay = overlay * (1 - a) + np.array([1.0, 0.45, 0.08]) * a

        # Red: ignition zone (user-drawn origin)
        a = (ignition * OVERLAY_OPACITY)[..., None]
        overlay = overlay * (1 - a) + np.array([0.92, 0.08, 0.08]) * a

        overlay = np.clip(overlay, 0, 1)
        overlay_img = Image.fromarray((overlay * 255).astype(np.uint8))
        buffer = io.BytesIO()
        overlay_img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"


PREDICTOR = DeepFirePredictor()
