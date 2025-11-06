import torch
print("CUDA 사용 가능 여부:", torch.cuda.is_available())
print("PyTorch가 인식한 CUDA 버전:", torch.version.cuda)
print("설치된 torch 버전:", torch.__version__)