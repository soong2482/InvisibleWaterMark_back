import torch
import torch.nn as nn
import torch.nn.functional as F

class SimpleConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x):
        return self.conv(x)

class DeepQRStructure(nn.Module):
    """깊고 강력한 QR 구조 임베딩"""
    def __init__(self, qr_channels):
        super().__init__()
        # 다중 스케일 QR 패턴 검출
        self.edge_1x1 = nn.Conv2d(qr_channels, 1, 1, bias=False)
        self.edge_3x3 = nn.Conv2d(qr_channels, 1, 3, padding=1, bias=False)  
        self.edge_5x5 = nn.Conv2d(qr_channels, 1, 5, padding=2, bias=False)
        self.edge_7x7 = nn.Conv2d(qr_channels, 1, 7, padding=3, bias=False)
        
        # 강력한 엣지 필터들
        sobel_3 = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32)
        sobel_5 = torch.tensor([
            [-2, -1, 0, 1, 2],
            [-3, -2, 0, 2, 3],
            [-4, -3, 0, 3, 4], 
            [-3, -2, 0, 2, 3],
            [-2, -1, 0, 1, 2]
        ], dtype=torch.float32) / 9.0
        sobel_7 = torch.ones((7, 7), dtype=torch.float32)
        sobel_7[3, :] = torch.tensor([-3, -2, -1, 0, 1, 2, 3], dtype=torch.float32)
        
        with torch.no_grad():
            self.edge_1x1.weight[0, 0] = torch.ones((1, 1), dtype=torch.float32)
            self.edge_3x3.weight[0, 0] = sobel_3
            self.edge_5x5.weight[0, 0] = sobel_5
            self.edge_7x7.weight[0, 0] = sobel_7
        
        # 다중 스케일 융합
        self.fusion = nn.Sequential(
            nn.Conv2d(4, 8, 3, padding=1),
            nn.ReLU(), 
            nn.Conv2d(8, 1, 1),
            nn.Sigmoid()
        )
        
    def forward(self, qr):
        edge_1 = torch.abs(self.edge_1x1(qr))
        edge_3 = torch.abs(self.edge_3x3(qr))
        edge_5 = torch.abs(self.edge_5x5(qr))
        edge_7 = torch.abs(self.edge_7x7(qr))
        
        multi_scale = torch.cat([edge_1, edge_3, edge_5, edge_7], dim=1)
        structure_importance = self.fusion(multi_scale)
        
        return structure_importance

class AggressiveEmbedder(nn.Module):
    """공격적 임베딩 모듈"""
    def __init__(self, channels):
        super().__init__()
        # 픽셀 단위까지 깊게 변조
        self.deep_modifier = nn.Sequential(
            nn.Conv2d(channels, channels * 2, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(channels * 2, channels * 2, 1),
            nn.ReLU(),
            nn.Conv2d(channels * 2, channels, 3, padding=1),
            nn.Tanh()
        )
        
        # 잔차 연결로 원본 + 강한 변화
        self.residual_weight = nn.Parameter(torch.tensor(2.0))  # 강한 잔차
        
    def forward(self, x):
        modification = self.deep_modifier(x)
        return x + modification * self.residual_weight

class DeepInvisibleQRNet(nn.Module):
    """적당히 강력한 QR 임베딩 네트워크 - Face swap 대응 + 디코더 친화적"""
    def __init__(self, in_channels=3, watermark_channels=1):
        super().__init__()
        
        # === 적당한 얼굴 인코더 ===
        self.face_encoder = nn.Sequential(
            SimpleConv(in_channels, 32),      # 경량 → 적당
            SimpleConv(32, 64),               # 추가 깊이
            SimpleConv(64, 64)                # 안정화
        )
        
        # === 적당한 QR 마스크 인코더 ===
        self.qr_mask_encoder = nn.Sequential(
            SimpleConv(watermark_channels, 16), 
            SimpleConv(16, 32),
            SimpleConv(32, 64)                # face_encoder와 맞춤
        )
        
        # === 강화된 QR 구조 (DeepQRStructure 간소화 버전) ===
        self.qr_structure = nn.ModuleDict({
            'edge_3x3': nn.Conv2d(watermark_channels, 1, 3, padding=1, bias=False),
            'edge_5x5': nn.Conv2d(watermark_channels, 1, 5, padding=2, bias=False),
        })
        
        # 다중 스케일 sobel 초기화
        sobel_3 = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32)
        sobel_5 = torch.tensor([
            [-1, -1, 0, 1, 1],
            [-2, -2, 0, 2, 2],
            [-2, -2, 0, 2, 2], 
            [-1, -1, 0, 1, 1],
            [-1, -1, 0, 1, 1]
        ], dtype=torch.float32) / 4.0
        
        with torch.no_grad():
            self.qr_structure['edge_3x3'].weight[0, 0] = sobel_3
            self.qr_structure['edge_5x5'].weight[0, 0] = sobel_5
        
        # 구조 융합
        self.structure_fusion = nn.Sequential(
            nn.Conv2d(2, 4, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(4, 1, 1),
            nn.Sigmoid()
        )
        
        # === 적당한 공격성 임베더 (AggressiveEmbedder 경량화) ===
        self.feature_enhancer = nn.Sequential(
            nn.Conv2d(64 + 64, 96, 3, padding=1),  # 적당한 확장
            nn.ReLU(),
            nn.Conv2d(96, 64, 1),                   # 압축
            nn.ReLU()
        )
        
        # === 2단계 델타 생성 ===
        self.delta_generator = nn.Sequential(
            nn.Conv2d(64, 32, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 16, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, in_channels, 3, padding=1),
            nn.Tanh()
        )
        
        # === 적당한 임베딩 파라미터들 ===
        self.base_strength = nn.Parameter(torch.tensor(0.08))       # 적당한 기본 강도
        self.structure_amplify = nn.Parameter(torch.tensor(1.5))    # 적당한 구조 증폭
        self.depth_factor = nn.Parameter(torch.tensor(0.3))         # 깊이 인자 추가
        
        # === 2단계 레이어 임베딩 (3단계 → 2단계) ===
        self.layer_weights = nn.Parameter(torch.tensor([1.0, 0.6]))
        
    def forward(self, face_img, qr_mask):
        # === 마스크 크기 자동 조정 ===
        if qr_mask.shape[2:] != face_img.shape[2:]:
            qr_mask = F.interpolate(qr_mask, size=face_img.shape[2:], mode='bilinear', align_corners=False)
        
        # === 적당한 특성 추출 ===
        face_feat = self.face_encoder(face_img)
        mask_feat = self.qr_mask_encoder(qr_mask)
        
        # === 강화된 QR 구조 맵 ===
        edge_3 = torch.abs(self.qr_structure['edge_3x3'](qr_mask))
        edge_5 = torch.abs(self.qr_structure['edge_5x5'](qr_mask))
        multi_edge = torch.cat([edge_3, edge_5], dim=1)
        structure_map = self.structure_fusion(multi_edge)
        
        # === 특성 강화 ===
        combined = torch.cat([face_feat, mask_feat], dim=1)
        enhanced_feat = self.feature_enhancer(combined)
        
        # === 델타 생성 ===
        delta = self.delta_generator(enhanced_feat)
        
        # === 적당한 임베딩 강도 맵 ===
        mask_binary = (qr_mask > 0.01).float()
        
        strength_map = (
            self.base_strength * 
            (1 + structure_map * self.structure_amplify) * 
            (1 + self.depth_factor) *
            mask_binary
        )
        
        # === 2단계 레이어 임베딩 ===
        watermarked = face_img.clone()
        
        # 1층: 표면 임베딩
        layer1_delta = delta * self.layer_weights[0]
        watermarked = watermarked + layer1_delta * strength_map
        
        # 2층: 중간층 임베딩 (적당한 블러)
        layer2_delta = F.avg_pool2d(delta, 3, stride=1, padding=1) * self.layer_weights[1]
        watermarked = watermarked + layer2_delta * strength_map * 0.8
        
        # === 최종 클램핑 ===
        watermarked = torch.clamp(watermarked, 0.0, 1.0)
        
        return watermarked, strength_map