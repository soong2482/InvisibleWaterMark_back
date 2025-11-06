# server/embed.py
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import StreamingResponse, PlainTextResponse
from io import BytesIO
from PIL import Image
import qrcode
import torch
from torchvision import transforms
from torchvision.transforms.functional import to_pil_image
from torchvision.utils import save_image
from ultralytics import YOLO
import os
import uuid
import sys
import traceback
import numpy as np
import cv2

# === 경로 확인 ===
print("🔥 sys.path 확인:")
for p in sys.path:
    print("   ", p)

# === 모듈 import ===
from embedmodel.invisible_watermark_generator import DeepInvisibleQRNet
from embedmodel.embed_watermark_inference import embed_qr_to_face_from_bytes
from decodemodel.decode_watermark_inference import decode_qr_from_image_byte
from decodemodel.decode_watermark_fake_inference import decode_like_training_return

app = FastAPI()

# === 모델 로드 ===
model = YOLO("yolov11l-face.pt")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
generator = DeepInvisibleQRNet().to(device)
generator.load_state_dict(torch.load("C:/Users/user/Desktop/server/embedmodel/generator.pth"))
generator.eval()

# === QR 코드 생성 함수 ===
def generate_qr_fixed_128(text: str) -> torch.Tensor:
    """QR 코드 생성 후 텐서로 변환 (추론 함수와 호환)"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=1,
    )
    qr.add_data(text)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.resize((92, 92), Image.LANCZOS).convert('L')
    
    # 텐서로 변환 (추론 함수에서 기대하는 형태)
    transform_qr = transforms.ToTensor()
    qr_tensor = transform_qr(qr_img).unsqueeze(0)
    
    return qr_tensor, qr_img  # 텐서와 PIL 이미지 둘 다 반환

# === /embed ===
@app.post("/embed")
async def embed_watermark(
    image: UploadFile = File(...),
    username: str = Form(...),
    text: str = Form(...)
):
    image_bytes = await image.read()
    
    # QR 코드 생성 (텐서와 PIL 이미지 둘 다 받기)
    qr_tensor, qr_pil = generate_qr_fixed_128(text)
    
    try:
        # 올바른 파라미터로 호출 (generator, yolo_model)
        output_img, _ = embed_qr_to_face_from_bytes(
            image_bytes, 
            qr_tensor,      # torch.Tensor
            generator,      # 생성 모델
            model      # YOLO 얼굴 감지 모델 (model → yolo_model로 수정)
        )
    except Exception as e:
        return {"error": str(e)}
    
    # 저장
    os.makedirs("outputs", exist_ok=True)
    file_id = str(uuid.uuid4())
    embedded_path = os.path.join("outputs", f"embedded_{file_id}.png")
    qr_path = os.path.join("outputs", f"qr_{file_id}.png")
    
    output_img.save(embedded_path)
    qr_pil.save(qr_path)  # PIL 이미지 저장
    
    # 응답
    buffer = BytesIO()
    output_img.save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/png")

# === /decode ===
@app.post("/decode")
async def decode_face(image: UploadFile = File(...)):
    image_bytes = await image.read()
    decoder = decode_qr_from_image_byte()
    try:
        print("✅ decode_face 함수 진입")
        result = decoder(image_bytes)
        print(result)
        return PlainTextResponse(content=result, status_code=200)
    except Exception as e:
        print("❌ 디코딩 중 오류 발생:", e)
        traceback.print_exc()
        return PlainTextResponse("decoding Conflit", status_code=200)

# === /decodeVIP ===
@app.post("/decodeVIP")
async def decode_face_VIP(image: UploadFile = File(...)):
    image_bytes = await image.read()
    try:
        print("✅ decode_face VIP 함수 진입")
        result = decode_like_training_return(image_bytes)
        print(result)
        return PlainTextResponse(content=result, status_code=200)
    except Exception as e:
        print("❌ 디코딩 중 오류 발생:", e)
        traceback.print_exc()
        return PlainTextResponse("decoding Conflit", status_code=200)

# === /detecting ===
@app.post("/detecting")
async def detect_faces(image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 이미지 리사이즈 (1024 최대 차원)
        h_img, w_img = img.shape[:2]
        max_dim = 1024
        scale = min(max_dim / max(h_img, w_img), 1)
        if scale < 1:
            new_w = int(w_img * scale)
            new_h = int(h_img * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            h_img, w_img = img.shape[:2]

        results = model(img)[0]
        boxes = results.boxes.xyxy

        found_valid_face = False
        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.tolist())
                
                # 정사각형 얼굴 영역 계산
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                bbox_w, bbox_h = x2 - x1, y2 - y1
                
                # 가로 기준 정사각형 크기, 짝수로 보정
                square_size = int(bbox_w)
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
                sx2 = min(w_img, sx2_ideal)
                sy2 = min(h_img, sy2_ideal)
                
                # 정사각형 보장을 위한 조정
                actual_w = sx2 - sx1
                actual_h = sy2 - sy1
                final_size = min(actual_w, actual_h)
                
                # 중심점 기준으로 재조정
                new_half = final_size // 2
                sx1_final = max(0, min(w_img - final_size, cx - new_half))
                sy1_final = max(0, min(h_img - final_size, cy - new_half))
                sx2_final = sx1_final + final_size
                sy2_final = sy1_final + final_size
                
                # 최종 크기 계산
                final_size = min(sx2_final - sx1_final, sy2_final - sy1_final)
                
                # 60 미만 조건으로 변경
                if final_size >= 60:
                    found_valid_face = True
                    break

        return PlainTextResponse("ok" if found_valid_face else "no face", status_code=200)

    except Exception as e:
        return PlainTextResponse(f"error: {str(e)}", status_code=500)
#uvicorn run:app --reload       