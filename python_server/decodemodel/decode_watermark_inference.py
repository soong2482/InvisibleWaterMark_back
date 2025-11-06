import os
import torch
import torch.nn.functional as F
from torchvision import transforms
import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
from pyzbar import pyzbar
import PIL.Image
import io

# 우리가 만든 패치 디코더 (훈련 코드에서 가져온 것과 동일해야 함)
from .decoder import MidPerformancePatchQRDecoder, QRPatchProcessor

class decode_qr_from_image_byte:
    def __init__(self, model_path="decodemodel\latest_patch_decoder.pth"):
        """
        QR 디코더 클래스 초기화
        
        Args:
            model_path (str): 훈련된 모델의 경로
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = model_path
        
        # 모델 초기화
        self.decoder = MidPerformancePatchQRDecoder(patch_size=64).to(self.device)
        self.processor = QRPatchProcessor(self.decoder)
        
        # YOLO 모델 로드 (얼굴 감지용)
        self.yolo = YOLO("yolov11l-face.pt").to("cpu")
        
        # 모델 가중치 로드
        self._load_model()
    
    def _load_model(self):
        """훈련된 모델 가중치 로드"""
        if os.path.exists(self.model_path):
            checkpoint = torch.load(self.model_path, map_location=self.device)
            self.decoder.load_state_dict(checkpoint)
            print(f"✅ 모델 로드 완료: {self.model_path}")
        else:
            print(f"❌ 모델 파일을 찾을 수 없습니다: {self.model_path}")
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
    
    def _get_face_region_for_decoder(self, bbox, img_width, img_height):
        """디코더용 얼굴 영역 계산 - 학습 코드와 동일"""
        x1, y1, x2, y2 = [int(x) for x in bbox]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        size = x2 - x1
        
        # 정사각형 영역
        half = size // 2
        sx1, sy1 = max(0, cx - half), max(0, cy - half)
        sx2, sy2 = min(img_width, sx1 + size), min(img_height, sy1 + size)
        
        return (sx1, sy1, sx2, sy2) if (sx2 - sx1) > 60 else None
    
    def _get_grid_size_for_decoder(self, face_size):
        """그리드 크기 결정 - 학습 코드와 동일"""
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
    
    def _decode_qr_from_tensor(self, qr_tensor, threshold=0.4):
        """텐서에서 QR 코드를 디코드"""
        try:
            # 텐서를 numpy 배열로 변환
            if qr_tensor.dim() == 4:  # [B, C, H, W]
                qr_np = qr_tensor[0, 0].detach().cpu().numpy()
            elif qr_tensor.dim() == 3:  # [C, H, W]
                qr_np = qr_tensor[0].detach().cpu().numpy()
            else:  # [H, W]
                qr_np = qr_tensor.detach().cpu().numpy()
            
            # 이진화
            qr_binary = (qr_np > threshold).astype(np.uint8) * 255
            
            # PIL 이미지로 변환
            qr_img = PIL.Image.fromarray(qr_binary)
            
            # QR 코드 디코드
            decoded_objects = pyzbar.decode(qr_img)
            
            if decoded_objects:
                return decoded_objects[0].data.decode('utf-8')
            else:
                return None
                
        except Exception as e:
            print(f"QR 디코딩 오류: {e}")
            return None
    
    def _load_image_from_bytes(self, image_bytes):
        """바이트 데이터에서 이미지를 로드하고 텐서로 변환"""
        try:
            # 바이트 데이터를 PIL 이미지로 변환
            img = PIL.Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            # 텐서로 변환 (0-1 범위)
            transform = transforms.Compose([
                transforms.ToTensor(),
            ])
            
            img_tensor = transform(img).unsqueeze(0).to(self.device)  # [1, 3, H, W]
            return img_tensor, img.size  # (width, height)
            
        except Exception as e:
            print(f"❌ 이미지 로드 실패: {e}")
            return None, None
    
    def __call__(self, image_bytes):
        """
        이미지 바이트에서 QR 코드를 디코딩
        
        Args:
            image_bytes: 이미지 바이트 데이터
            
        Returns:
            str or None: 디코딩된 QR 텍스트 또는 None (실패시)
        """
        try:
            # 이미지 로드
            watermarked, img_size = self._load_image_from_bytes(image_bytes)
            
            if watermarked is None:
                print("❌ 이미지 로드 실패")
                return None
            
            print(f"📊 이미지 크기: {img_size[0]}x{img_size[1]}")
            
            h, w = watermarked.shape[2:]
            face_np = (watermarked[0].permute(1, 2, 0).detach().cpu().numpy() * 255).astype(np.uint8)
            
            # 얼굴 검출
            print("👤 얼굴 검출 중...")
            with torch.no_grad():
                yolo_result = self.yolo(face_np, conf=0.3, verbose=False)[0]
            boxes = yolo_result.boxes.xyxy.cpu().numpy() if yolo_result.boxes else []
            
            if len(boxes) == 0:
                print("❌ 얼굴을 찾을 수 없습니다.")
                return None
            
            print(f"✅ {len(boxes)}개의 얼굴 검출됨")
            
            # 가장 큰 얼굴 선택
            areas = [(x2-x1)*(y2-y1) for (x1, y1, x2, y2) in boxes]
            bbox = boxes[areas.index(max(areas))]
            face_region = self._get_face_region_for_decoder(bbox, w, h)
            
            if face_region is None:
                print("❌ 얼굴 영역이 너무 작거나 경계를 벗어났습니다.")
                return None
            
            print(f"📐 얼굴 영역: {face_region}")
            
            # 그리드 크기 결정
            face_size = face_region[2] - face_region[0]
            grid_size = self._get_grid_size_for_decoder(face_size)
            print(f"🔳 그리드 크기: {grid_size}x{grid_size}")
            
            # 패치 처리로 QR 복원
            print("🔄 QR 복원 중...")
            try:
                result = self.processor.process_face_patches(
                    watermarked, face_region, grid_size, target_qr_size=(92, 92)
                )
            except Exception as patch_error:
                print(f"❌ 패치 처리 중 오류: {patch_error}")
                return None
            
            if result[0] is None:
                print("❌ 패치 처리 실패")
                return None
            
            final_qr, avg_confidence, patch_qrs, positions = result
            
            # avg_confidence가 텐서인 경우 처리
            try:
                if hasattr(avg_confidence, 'item'):
                    confidence_val = avg_confidence.item()
                elif isinstance(avg_confidence, (int, float)):
                    confidence_val = float(avg_confidence)
                else:
                    confidence_val = 0.0
            except:
                confidence_val = 0.0
                
            print(f"✅ QR 복원 완료 (신뢰도: {confidence_val:.3f})")
            
            # 복원된 QR 코드에서 텍스트 추출
            print("📖 QR 코드 디코딩 중...")
            decoded_text = self._decode_qr_from_tensor(final_qr)
            
            if decoded_text is not None:
                print(f"✅ QR 인식 성공!")
                print(f"📝 디코딩된 텍스트: {decoded_text}")
                return decoded_text
            else:
                print("❌ QR 인식 실패")
                return "decoding failed"
                
        except Exception as e:
            print(f"❌ QR 디코딩 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return "decoding failed"