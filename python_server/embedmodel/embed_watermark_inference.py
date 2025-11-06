import io
import os
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset
from torchvision import transforms
import numpy as np
from PIL import Image
import random

def resize_with_aspect_ratio(img, max_dim=1024):
    """이미지를 비율을 유지하면서 최대 차원을 1024로 리사이즈"""
    h, w = img.shape[:2]
    scale = min(max_dim / max(h, w), 1)
    resized = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return resized, scale

def get_square_face_region_perfect(bbox, img_width, img_height):
    """완벽한 정사각형 얼굴 영역 계산 (타입 안정성 개선)"""
    x1, y1, x2, y2 = [int(x) for x in bbox]  # 모든 좌표를 정수로 변환
    
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    bbox_w, bbox_h = x2 - x1, y2 - y1
    
    # 가로 기준 정사각형 크기, 짝수로 보정
    square_size = int(bbox_w)  # 정수 변환 추가
    if square_size % 2 == 1:
        square_size += 1
    
    half = square_size // 2
    
    # 초기 정사각형 영역 계산
    sx1_ideal = cx - half
    sy1_ideal = cy - half
    sx2_ideal = cx + half
    sy2_ideal = cy + half
    
    # 경계 제약 적용
    sx1 = max(0, sx1_ideal)
    sy1 = max(0, sy1_ideal)
    sx2 = min(img_width, sx2_ideal)
    sy2 = min(img_height, sy2_ideal)
    
    # 정사각형 보장을 위한 조정
    actual_w = sx2 - sx1
    actual_h = sy2 - sy1
    final_size = min(actual_w, actual_h)
    
    # 중심점 기준으로 재조정
    new_half = final_size // 2
    sx1_final = max(0, min(img_width - final_size, cx - new_half))
    sy1_final = max(0, min(img_height - final_size, cy - new_half))
    sx2_final = sx1_final + final_size
    sy2_final = sy1_final + final_size
    
    # 최소 크기 체크 (100으로 변경)
    if final_size < 60:
        return None
    
    # 경계 체크
    if (sx2_final > img_width or sy2_final > img_height or 
        sx1_final < 0 or sy1_final < 0):
        return None
        
    # 모든 좌표를 정수로 반환
    return (int(sx1_final), int(sy1_final), int(sx2_final), int(sy2_final))

def get_embedding_compatible_grid_size(face_size):
    """그리드 크기 결정 (첫 번째 코드와 동일)"""
    if face_size < 150:
        return 2
    elif face_size < 200:
        return 3
    elif face_size < 256:
        return 4
    elif face_size < 320:
        return 5
    elif face_size < 400:
        return 6
    elif face_size < 512:
        return 7
    elif face_size < 640:
        return 8
    elif face_size < 768:
        return 9
    elif face_size < 1024:
        return 10
    else:
        return 11

def create_qr_mask_perfect_grid(qr_image, face_region, img_height, img_width, qr_strength_module, device):
    """완벽한 그리드 정렬 QR 마스크 생성 (타입 안정성 개선)"""
    sx1, sy1, sx2, sy2 = [int(x) for x in face_region]  # 타입 변환 추가
    
    # 얼굴 영역 정사각형 보정
    face_w, face_h = sx2 - sx1, sy2 - sy1
    if face_w != face_h:
        min_size = min(face_w, face_h)
        center_x = int((sx1 + sx2) // 2)  # 명시적 정수 변환
        center_y = int((sy1 + sy2) // 2)  # 명시적 정수 변환
        half = int(min_size // 2)  # 명시적 정수 변환
        sx1, sy1 = center_x - half, center_y - half
        sx2, sy2 = sx1 + min_size, sy1 + min_size
        face_w = face_h = min_size
    
    # 그리드 크기 결정
    grid = get_embedding_compatible_grid_size(face_w)
    
    # 그리드로 완벽하게 나누어떨어지는 크기 계산
    min_patch_size = 26
    max_possible_size = (face_w // grid) * grid
    
    if max_possible_size // grid < min_patch_size:
        return None, grid, None
    
    target_size = max_possible_size
    patch_size = target_size // grid
    
    # 얼굴 영역을 target_size로 조정
    if target_size != face_w:
        shrink = face_w - target_size
        sx1 += shrink // 2
        sy1 += shrink // 2
        sx2 = sx1 + target_size
        sy2 = sy1 + target_size
    
    # QR 강도 가져오기
    with torch.no_grad():
        current_qr_strength = qr_strength_module()
    
    # 마스크 생성
    mask = torch.zeros((1, 1, img_height, img_width), device=device)
    
    # QR 이미지 차원 정규화
    if qr_image.dim() == 3:
        qr_resized = qr_image.unsqueeze(0)
    else:
        qr_resized = qr_image
    
    # 그리드 기준 패치 생성
    for gy in range(grid):
        for gx in range(grid):
            px1 = sx1 + gx * patch_size
            py1 = sy1 + gy * patch_size
            px2 = px1 + patch_size
            py2 = py1 + patch_size
            
            # 모든 좌표를 정수로 변환 (에러 방지)
            px1, py1, px2, py2 = int(px1), int(py1), int(px2), int(py2)
            
            # 경계 체크
            if px2 > sx2 or py2 > sy2 or px1 < sx1 or py1 < sy1:
                continue
            
            if px2 - px1 <= 1 or py2 - py1 <= 1:
                continue
            
            # QR 리사이즈 (크기를 int로 변환)
            patch_h, patch_w = py2 - py1, px2 - px1
            if patch_h > 0 and patch_w > 0:
                patch = F.interpolate(
                    qr_resized, 
                    size=(int(patch_h), int(patch_w)),  # 명시적 정수 변환
                    mode="bilinear", 
                    align_corners=True
                )
                
                # 마스크 적용
                mask[:, :, py1:py2, px1:px2] = patch * current_qr_strength
    
    return mask, grid, (int(patch_size), int(patch_size))  # 튜플도 정수로 변환

def embed_qr_to_face_from_bytes(image_bytes, qr_tensor, generator, yolo_model):
    device = next(generator.parameters()).device

    class TempQRStrength(nn.Module):
        def __init__(self, strength=20.0):
            super().__init__()
            self.strength = torch.tensor(strength)
        def forward(self):
            return self.strength
        def get_strength(self):
            return self.strength.item()
    
    qr_strength_module = TempQRStrength().to(device)
    
    # 이미지 로드 및 EXIF 방향 정보 처리
    face_img = Image.open(io.BytesIO(image_bytes))
    
    # EXIF 방향 정보에 따라 이미지 회전
    try:
        exif = face_img._getexif()
        if exif is not None:
            orientation = exif.get(274)  # 274는 Orientation 태그
            if orientation == 3:
                face_img = face_img.rotate(180, expand=True)
            elif orientation == 6:
                face_img = face_img.rotate(270, expand=True)
            elif orientation == 8:
                face_img = face_img.rotate(90, expand=True)
    except:
        pass  # EXIF 정보가 없거나 읽을 수 없는 경우 무시
    
    face_img = face_img.convert('RGB')
    original_size = face_img.size
    
    # PIL을 numpy로 변환하여 리사이즈 (색상 공간 변환 최소화)
    face_np = np.array(face_img)
    face_resized, scale = resize_with_aspect_ratio(face_np, max_dim=1024)
    
    # 리사이즈된 이미지를 PIL로 변환
    face_img = Image.fromarray(face_resized)
    
    # 텐서 변환
    transform_face = transforms.ToTensor()
    face_tensor = transform_face(face_img).unsqueeze(0).to(device)
    qr_tensor = qr_tensor.to(device)
    
    # 얼굴 감지
    face_np = (face_tensor[0].permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
    with torch.no_grad():
        result = yolo_model(face_np, conf=0.3, verbose=False)[0]
    boxes = result.boxes.xyxy.cpu().numpy() if result.boxes else []
    
    if len(boxes) == 0:
        raise ValueError("❌ 얼굴을 찾을 수 없습니다.")
    
    # 가장 큰 얼굴 선택
    areas = [(x2 - x1) * (y2 - y1) for (x1, y1, x2, y2) in boxes]
    x1, y1, x2, y2 = boxes[areas.index(max(areas))]
    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
    face_bbox = (x1, y1, x2, y2)
    
    # 얼굴 크기 확인 (100으로 변경)
    face_width = x2 - x1
    face_height = y2 - y1
    min_face_size = 60  # 100으로 변경
    
    if face_width < min_face_size or face_height < min_face_size:
        raise ValueError("❌ 얼굴 크기가 너무 작습니다.")
    
    # 정사각형 얼굴 영역 계산
    _, _, h, w = face_tensor.shape
    face_region = get_square_face_region_perfect(face_bbox, w, h)
    
    if face_region is None:
        raise ValueError("❌ 적절한 얼굴 영역을 찾을 수 없습니다.")
    
    # 그리드 정렬 QR 마스크 생성
    mask_result = create_qr_mask_perfect_grid(qr_tensor, face_region, h, w, qr_strength_module, device)
    
    if mask_result[0] is None:
        raise ValueError("❌ QR 마스크 생성에 실패했습니다.")
    
    mask, grid, patch_size = mask_result
    
    # 워터마크 적용
    with torch.no_grad():
        watermarked, strength = generator(face_tensor, mask)
        
        # 출력 크기 조정
        if watermarked.shape != face_tensor.shape:
            watermarked = F.interpolate(
                watermarked, 
                size=face_tensor.shape[2:], 
                mode="bilinear", 
                align_corners=True
            )
        
        # PIL 이미지로 변환
        result_np = watermarked[0].permute(1, 2, 0).cpu().numpy()
        result_np = np.clip(result_np * 255, 0, 255).astype(np.uint8)
        result_pil = Image.fromarray(result_np)
        
        
    return result_pil, {
        'face_bbox': face_bbox,
        'face_region': face_region,
        'grid': grid,
        'patch_size': patch_size,
        'qr_strength': qr_strength_module.get_strength(),
        'scale': scale,
        'original_size': original_size
    }