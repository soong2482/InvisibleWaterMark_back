import torch
import torch.nn as nn
import torch.nn.functional as F

class LightResidualBlock(nn.Module):
    """경량 잔차 블록"""
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
        
    def forward(self, x):
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        return self.relu(out)

class ChannelAttention(nn.Module):
    """간단한 채널 어텐션"""
    def __init__(self, channels, reduction=8):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Conv2d(channels, channels // reduction, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels // reduction, channels, 1, bias=False),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        attention = self.fc(self.avg_pool(x))
        return x * attention

class EnhancedConvBlock(nn.Module):
    """향상된 컨볼루션 블록 - 적당한 복잡도"""
    def __init__(self, in_channels, out_channels, num_blocks=2):
        super().__init__()
        
        # 입력 채널 조정
        self.input_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        
        # 경량 잔차 블록들
        self.res_blocks = nn.ModuleList([
            LightResidualBlock(out_channels) for _ in range(num_blocks)
        ])
        
        # 채널 어텐션만 사용 (공간 어텐션 제거)
        self.channel_attention = ChannelAttention(out_channels)
        
    def forward(self, x):
        x = self.input_conv(x)
        
        # 잔차 블록들 통과
        for res_block in self.res_blocks:
            x = res_block(x)
        
        # 채널 어텐션만 적용
        x = self.channel_attention(x)
        
        return x

class DualScaleExtractor(nn.Module):
    """2개 스케일만 사용하는 특성 추출기"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        
        # 2개 스케일만 사용
        self.scale1 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels // 2, 3, padding=1),
            nn.BatchNorm2d(out_channels // 2),
            nn.ReLU(inplace=True)
        )
        
        self.scale2 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels // 2, 5, padding=2),
            nn.BatchNorm2d(out_channels // 2),
            nn.ReLU(inplace=True)
        )
        
        # 간단한 융합
        self.fusion = nn.Sequential(
            nn.Conv2d(out_channels, out_channels, 1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        
    def forward(self, x):
        s1 = self.scale1(x)
        s2 = self.scale2(x)
        
        # 연결 및 융합
        combined = torch.cat([s1, s2], dim=1)
        return self.fusion(combined)

class MidPerformancePatchQRDecoder(nn.Module):
    """중간 성능 패치별 QR 복원 디코더 - 균형잡힌 버전"""
    def __init__(self, patch_size=64):
        super().__init__()
        self.patch_size = patch_size
        
        # === 패치 특성 추출기 (적당한 복잡도) ===
        self.patch_encoder = nn.Sequential(
            DualScaleExtractor(3, 64),              # RGB → 64채널
            EnhancedConvBlock(64, 96, num_blocks=2), # 96채널로 확장
            nn.Conv2d(96, 96, 3, padding=1),        # 최종 정제
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True)
        )
        
        # === 차이 증폭 분석기 (경량화) ===
        self.diff_analyzer = nn.Sequential(
            DualScaleExtractor(3, 32),              # 차이 이미지 → 32채널
            EnhancedConvBlock(32, 48, num_blocks=2), # 48채널로 확장
            nn.Conv2d(48, 48, 3, padding=1),        # 최종 정제
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True)
        )
        
        # === 구조 감지기 (간소화) ===
        self.structure_detector = nn.ModuleDict({
            'edge_3x3': nn.Conv2d(3, 4, 3, padding=1),  # 4개 필터로 축소
            'edge_5x5': nn.Conv2d(3, 4, 5, padding=2),
        })
        
        # 구조 특성 융합 (간소화)
        self.structure_fusion = nn.Sequential(
            nn.Conv2d(8, 24, 3, padding=1),         # 8채널 입력
            nn.BatchNorm2d(24),
            nn.ReLU(inplace=True),
            LightResidualBlock(24)                  # 1개 블록만
        )
        
        # === 특성 융합 (중간 복잡도) ===
        # 총 입력: 96 + 48 + 24 = 168채널
        self.feature_fusion = nn.Sequential(
            nn.Conv2d(168, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            ChannelAttention(128),
            LightResidualBlock(128),
            LightResidualBlock(128),
            nn.Conv2d(128, 96, 3, padding=1),
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True)
        )
        
        # === QR 복원기 (적당한 깊이) ===
        self.qr_reconstructor = nn.Sequential(
            nn.Conv2d(96, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            LightResidualBlock(64),
            nn.Conv2d(64, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.Conv2d(16, 1, 3, padding=1),  # 1채널 QR 출력
            nn.Sigmoid()
        )
        
        # === 신뢰도 예측기 (경량화) ===
        self.confidence_predictor = nn.Sequential(
            nn.Conv2d(96, 48, 3, padding=1),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True),
            nn.Conv2d(48, 24, 3, padding=1),
            nn.BatchNorm2d(24),
            nn.ReLU(inplace=True),
            nn.Conv2d(24, 1, 1),
            nn.Sigmoid()
        )
        
        # 가중치 초기화
        self._initialize_weights()
        
    def _initialize_weights(self):
        """가중치 초기화"""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
        
        # 구조 감지기 초기화 (간소화)
        with torch.no_grad():
            # 3x3 Sobel
            sobel_3 = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32)
            # 5x5 Sobel
            sobel_5 = torch.tensor([
                [-1, -1, 0, 1, 1], [-2, -2, 0, 2, 2], [-2, -2, 0, 2, 2], 
                [-1, -1, 0, 1, 1], [-1, -1, 0, 1, 1]
            ], dtype=torch.float32) / 4.0
            
            # 4개 필터에만 적용
            for c in range(3):
                for i in range(4):
                    if i < 2:
                        self.structure_detector['edge_3x3'].weight[i, c] = sobel_3 * (1 + 0.2 * i)
                        self.structure_detector['edge_5x5'].weight[i, c] = sobel_5 * (1 + 0.2 * i)
                    else:
                        # 회전된 필터
                        self.structure_detector['edge_3x3'].weight[i, c] = torch.rot90(sobel_3, i-2)
                        self.structure_detector['edge_5x5'].weight[i, c] = torch.rot90(sobel_5, i-2)
    
    def safe_background_estimation(self, x):
        """간단한 배경 추정"""
        batch_size, channels, h, w = x.shape
        
        if h < 16 or w < 16:
            bg = x.mean(dim=(2, 3), keepdim=True).expand_as(x)
            assert bg.dim() == 4, f"Background estimation result should be 4D"
            return bg
        
        # 2개 스케일만 사용
        kernel_sizes = [5, 7]
        backgrounds = []
        
        for kernel_size in kernel_sizes:
            if h >= kernel_size and w >= kernel_size:
                padding = kernel_size // 2
                try:
                    bg = F.avg_pool2d(x, kernel_size, stride=1, padding=padding)
                    if bg.shape[2:] != x.shape[2:]:
                        bg = F.interpolate(bg, size=x.shape[2:], mode='bilinear', align_corners=False)
                    backgrounds.append(bg)
                except:
                    pass
        
        if len(backgrounds) > 0:
            final_bg = torch.mean(torch.stack(backgrounds), dim=0)
        else:
            final_bg = x.mean(dim=(2, 3), keepdim=True).expand_as(x)
        
        assert final_bg.dim() == 4, f"Background estimation result should be 4D"
        return final_bg
    
    def safe_structure_detection(self, x):
        """간소화된 구조 감지"""
        try:
            if x.dim() != 4:
                raise ValueError(f"Expected 4D tensor, got {x.dim()}D")
            
            batch_size, channels, h, w = x.shape
            
            # 최소 크기 보장
            if h < 5 or w < 5:
                pad_h = max(0, 5 - h)
                pad_w = max(0, 5 - w)
                x = F.pad(x, (pad_w//2, pad_w - pad_w//2, pad_h//2, pad_h - pad_h//2))
            
            # 2개 스케일 엣지 감지만
            edges = []
            for name, detector in self.structure_detector.items():
                edge = torch.abs(detector(x))
                edges.append(edge)
            
            # 연결
            combined_edges = torch.cat(edges, dim=1)
            
            # 구조 특성 융합
            structure_feat = self.structure_fusion(combined_edges)
            
            return structure_feat
            
        except Exception as e:
            print(f"Structure detection fallback: {e}")
            device = x.device if hasattr(x, 'device') else torch.device('cpu')
            batch_size = x.shape[0] if x.dim() >= 1 else 1
            h = x.shape[2] if x.dim() >= 3 else 64
            w = x.shape[3] if x.dim() >= 4 else 64
            return torch.zeros(batch_size, 24, h, w, device=device)
    
    def forward_single_patch(self, watermarked_patch):
        """단일 패치에서 QR 복원 - 중간 성능 버전"""
        try:
            # 입력 검증
            if watermarked_patch.dim() == 3:
                watermarked_patch = watermarked_patch.unsqueeze(0)
            elif watermarked_patch.dim() != 4:
                raise ValueError(f"Expected 3D or 4D tensor, got {watermarked_patch.dim()}D")
            
            batch_size, channels, h, w = watermarked_patch.shape
            
            if channels != 3:
                raise ValueError(f"Expected 3 channels, got {channels}")
            
            # === 배경 추정 ===
            estimated_bg = self.safe_background_estimation(watermarked_patch)
            
            # === 차이 이미지 생성 ===
            diff_img = torch.abs(watermarked_patch - estimated_bg)
            assert diff_img.dim() == 4, f"diff_img should be 4D"
            
            # 적당한 증폭 (덜 공격적)
            amplification_factor = min(500, max(100, 5000 // max(h, w)))
            amplified_diff = torch.clamp(diff_img * amplification_factor, 0, 1)
            assert amplified_diff.dim() == 4, f"amplified_diff should be 4D"
            
            # === 특성 추출 ===
            patch_feat = self.patch_encoder(watermarked_patch)
            diff_feat = self.diff_analyzer(amplified_diff)
            
            assert patch_feat.dim() == 4, f"patch_feat should be 4D"
            assert diff_feat.dim() == 4, f"diff_feat should be 4D"
            
            # === 구조 감지 ===
            structure_feat = self.safe_structure_detection(amplified_diff)
            assert structure_feat.dim() == 4, f"structure_feat should be 4D"
            
            # === 크기 일치화 ===
            target_h, target_w = patch_feat.shape[2], patch_feat.shape[3]
            
            if diff_feat.shape[2:] != (target_h, target_w):
                diff_feat = F.interpolate(diff_feat, size=(target_h, target_w), 
                                        mode='bilinear', align_corners=False)
            
            if structure_feat.shape[2:] != (target_h, target_w):
                structure_feat = F.interpolate(structure_feat, size=(target_h, target_w), 
                                             mode='bilinear', align_corners=False)
            
            # === 특성 융합 ===
            combined_feat = torch.cat([patch_feat, diff_feat, structure_feat], dim=1)
            assert combined_feat.dim() == 4, f"combined_feat should be 4D"
            
            # === 융합된 특성 처리 ===
            fused_feat = self.feature_fusion(combined_feat)
            
            # === QR 복원 ===
            restored_qr = self.qr_reconstructor(fused_feat)
            confidence = self.confidence_predictor(fused_feat)
            
            # 4D 차원 유지 최종 확인
            assert restored_qr.dim() == 4, f"restored_qr should be 4D"
            assert confidence.dim() == 4, f"confidence should be 4D"
            
            return restored_qr, confidence
            
        except Exception as e:
            print(f"Error in forward_single_patch: {e}")
            import traceback
            traceback.print_exc()
            
            # 폴백: 기본 크기 텐서 반환
            device = watermarked_patch.device if hasattr(watermarked_patch, 'device') else torch.device('cpu')
            h = watermarked_patch.shape[2] if watermarked_patch.dim() >= 3 else 64
            w = watermarked_patch.shape[3] if watermarked_patch.dim() >= 4 else 64
            
            return (torch.zeros(1, 1, h, w, device=device), 
                   torch.zeros(1, 1, h, w, device=device))
    
    def forward_batch_patches(self, patch_batch):
        """배치 패치들을 한번에 처리"""
        if patch_batch.dim() != 4:
            raise ValueError(f"Expected 4D tensor, got {patch_batch.dim()}D with shape {patch_batch.shape}")
        
        batch_size = patch_batch.shape[0]
        restored_qrs = []
        confidences = []
        
        for i in range(batch_size):
            single_patch = patch_batch[i:i+1]  # (1, 3, H, W) 유지
            qr, conf = self.forward_single_patch(single_patch)
            restored_qrs.append(qr)
            confidences.append(conf)
        
        restored_qrs = torch.cat(restored_qrs, dim=0)
        confidences = torch.cat(confidences, dim=0)
        
        return restored_qrs, confidences
    
    def average_patches_to_qr(self, patch_qrs, confidences, target_qr_size=(92, 92)):
        """패치들의 QR을 평균내어 최종 QR 생성 - 간단한 가중 평균"""
        if patch_qrs is None or patch_qrs.numel() == 0:
            raise ValueError("patch_qrs is empty or None")
        
        batch_size = patch_qrs.shape[0]
        device = patch_qrs.device
        
        # target_qr_size 검증
        if isinstance(target_qr_size, (tuple, list)) and len(target_qr_size) >= 2:
            target_size = target_qr_size[:2]
        else:
            target_size = (92, 92)
        
        # 각 패치를 개별적으로 리사이즈
        resized_qrs = []
        resized_confs = []
        
        for i in range(batch_size):
            single_qr = patch_qrs[i:i+1]
            single_conf = confidences[i:i+1]
            
            try:
                resized_qr = F.interpolate(single_qr, size=target_size, 
                                         mode='bilinear', align_corners=False)
                resized_conf = F.interpolate(single_conf, size=target_size, 
                                           mode='bilinear', align_corners=False)
                
                resized_qrs.append(resized_qr)
                resized_confs.append(resized_conf)
                
            except Exception as e:
                # 폴백
                fallback_qr = torch.zeros(1, 1, target_size[0], target_size[1], device=device)
                fallback_conf = torch.zeros(1, 1, target_size[0], target_size[1], device=device)
                resized_qrs.append(fallback_qr)
                resized_confs.append(fallback_conf)
        
        # 배치로 결합
        resized_qrs_batch = torch.cat(resized_qrs, dim=0)
        resized_confs_batch = torch.cat(resized_confs, dim=0)
        
        # 간단한 신뢰도 기반 가중 평균
        weights = resized_confs_batch + 0.1  # 더 보수적인 가중치
        sum_weights = torch.sum(weights, dim=0, keepdim=True)
        
        # 가중 평균
        weighted_qrs = resized_qrs_batch * weights
        averaged_qr = torch.sum(weighted_qrs, dim=0, keepdim=True) / sum_weights
        avg_confidence = torch.mean(resized_confs_batch, dim=0, keepdim=True)
        
        return averaged_qr, avg_confidence

class QRPatchProcessor:
    """패치 분할 및 QR 복원 전체 과정"""
    def __init__(self, decoder_model):
        self.decoder = decoder_model
    
    def process_face_patches(self, face_img, face_region, grid_size, target_qr_size=(92, 92)):
        """패치 기반 QR 복원"""
        try:
            sx1, sy1, sx2, sy2 = face_region
            face_size = sx2 - sx1
            patch_size = face_size // grid_size
            
            device = face_img.device
            patches = []
            patch_positions = []
            
            # 패치 추출
            for gy in range(grid_size):
                for gx in range(grid_size):
                    px1 = sx1 + gx * patch_size
                    py1 = sy1 + gy * patch_size
                    px2 = px1 + patch_size
                    py2 = py1 + patch_size
                    
                    # 경계 확인
                    if px2 <= sx2 and py2 <= sy2:
                        patch = face_img[:, :, py1:py2, px1:px2]
                        if patch.shape[2] > 0 and patch.shape[3] > 0:
                            patches.append(patch)
                            patch_positions.append((gx, gy, px1, py1, px2, py2))
            
            if len(patches) == 0:
                return None, None, None, None
            
            # 패치 배치 생성
            patches_batch = torch.cat(patches, dim=0)
            
            # 패치별 QR 복원
            patch_qrs, patch_confidences = self.decoder.forward_batch_patches(patches_batch)
            
            # 최종 QR 생성
            final_qr, avg_confidence = self.decoder.average_patches_to_qr(
                patch_qrs, patch_confidences, target_qr_size
            )
            
            return final_qr, avg_confidence, patch_qrs, patch_positions
            
        except Exception as e:
            print(f"Error in process_face_patches: {e}")
            return None, None, None, None

# === 파라미터 수 확인 함수 ===
def count_parameters(model):
    """모델의 파라미터 수 계산"""
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return total_params, trainable_params

# === 테스트 함수 ===
def test_mid_decoder():
    """중간 성능 디코더 테스트"""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Testing Mid-Performance Patch QR Decoder on device: {device}")
    
    # 모델 생성
    decoder = MidPerformancePatchQRDecoder(patch_size=64).to(device)
    processor = QRPatchProcessor(decoder)
    
    # 파라미터 수 확인
    total_params, trainable_params = count_parameters(decoder)
    print(f"📊 Mid Model Parameters: {trainable_params:,} / {total_params:,}")
    
    # 기존 모델과 비교
    print(f"📈 기존 모델 대비: ~{trainable_params/270000:.1f}x 증가 (약 {trainable_params//1000}K 파라미터)")
    
    # 테스트 데이터
    test_sizes = [(65, 65), (128, 128)]
    
    for h, w in test_sizes:
        print(f"\n=== Testing size {h}x{w} ===")
        
        face_img = torch.randn(1, 3, h+50, w+50).to(device)
        face_region = (25, 25, 25+h, 25+w)
        grid_size = 2
        
        try:
            with torch.no_grad():  # 메모리 절약
                result = processor.process_face_patches(face_img, face_region, grid_size)
                
                if result[0] is not None:
                    final_qr, confidence, patch_qrs, positions = result
                    print(f"✅ Success: final_qr={final_qr.shape}, confidence={confidence.shape}")
                    print(f"   QR range: [{final_qr.min():.3f}, {final_qr.max():.3f}]")
                    print(f"   Confidence range: [{confidence.min():.3f}, {confidence.max():.3f}]")
                    print(f"   Patches processed: {len(positions) if positions else 0}")
                else:
                    print(f"❌ Processing failed")
                    
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_mid_decoder()