# WaterMark Backend

워터마크 임베딩/디코딩 서비스를 제공하는 백엔드 시스템입니다. Java Spring Boot 기반의 인증/인가 서버와 Python FastAPI 기반의 AI 워터마크 처리 서버로 구성됩니다.

## 프로젝트 구조

```
WaterMark_Back/
├── java_server/          # Spring Boot 인증/인가 서버
│   ├── src/main/java/    # Java 소스 코드
│   └── src/main/resources/ # 설정 파일
└── python_server/        # FastAPI 워터마크 처리 서버
    ├── embedmodel/       # 워터마크 임베딩 모델
    ├── decodemodel/      # 워터마크 디코딩 모델
    └── outputs/          # 처리된 이미지 출력 디렉토리
```

---

## Java Server (인증/인가 서버)

### 기술 스택
- **Framework**: Spring Boot 3.2.5
- **Java Version**: JDK 17
- **Build Tool**: Gradle
- **Security**: Spring Security + JWT + Redis Session
- **Database**: MariaDB (MyBatis)
- **Session Store**: Redis

### 주요 기능
- 회원가입 (이메일 인증)
- 로그인/로그아웃 (세션 + JWT 이중 인증)
- 리프레시 토큰 기반 지속 인증
- Role 기반 권한 관리 (USER, ADMIN, SUPER_ADMIN)
- 보안에 민감한 API: 세션 + JWT 이중 인증
- 일반 API: JWT 인증만으로 처리 (성능 최적화)

### 프로젝트 구조 설명
세션과 JWT를 결합하여 보안과 성능을 모두 고려한 인증 시스템을 구현했습니다:
- **세션**: 서버에서의 안정적인 사용자 관리와 저장
- **JWT**: 무상태 인증 및 보안
- **보안에 민감한 API**: 세션 + JWT 이중 인증으로 이중 보안 제공
- **일반 API**: JWT 인증만으로 처리하여 성능 향상
- **리프레시 토큰**: 지속적인 인증 유지 및 토큰 탈취 시 세션을 통한 관리 가능

### 실행 방법

#### 1. 사전 요구사항
- JDK 17 이상
- MariaDB (localhost:3306)
- Redis (localhost:6379)

#### 2. 설정 파일 준비
```bash
# 로컬 개발 환경 설정 (템플릿 복사 후 실제 값 입력)
cp java_server/src/main/resources/application-local.properties.example \
   java_server/src/main/resources/application-local.properties
```

#### 3. 서버 실행
```bash
cd java_server

# Gradle로 실행 (권장)
.\gradlew.bat bootRun

# 또는 JAR 파일로 실행
.\gradlew.bat build
java -jar build/libs/SecurityMVC-0.0.1-SNAPSHOT.jar
```

#### 4. 서버 접속
- 기본 주소: `http://localhost:8080`

### 설정 파일 관리

#### 구조
- **application.properties**: 공통 설정 (Git에 포함)
- **application-local.properties**: 로컬 개발 환경 설정 (Git에서 제외, 민감 정보 포함)
- **application-prod.properties**: 운영 환경 설정 (Git에서 제외, 민감 정보 포함)
- **application-*.properties.example**: 템플릿 파일 (Git에 포함)

#### 프로파일 변경
`application.properties`에서 `spring.profiles.active` 값을 변경:
- 로컬 개발: `spring.profiles.active=local`
- 운영 환경: `spring.profiles.active=prod`

#### 보안 주의사항
- ❌ **절대 Git에 민감한 정보를 포함한 properties 파일을 커밋하지 마세요**
- ✅ `.gitignore`에 `application-*.properties`가 포함되어 있어 자동으로 제외됩니다
- ✅ 템플릿 파일(`*.example`)만 Git에 포함됩니다
- ✅ 새로운 팀원은 템플릿 파일을 복사하여 자신의 설정 파일을 생성해야 합니다

---

## Python Server (워터마크 처리 서버)

### 기술 스택
- **Framework**: FastAPI
- **Python Version**: Python 3.10+
- **AI/ML**: PyTorch, YOLO (얼굴 감지)
- **Image Processing**: PIL, OpenCV, qrcode

### 주요 기능
- **워터마크 임베딩**: 이미지의 얼굴 영역에 QR 코드 워터마크를 비가시적으로 임베딩
- **워터마크 디코딩**: 임베딩된 워터마크를 추출 및 디코딩
- **VIP 디코딩**: 고급 디코딩 모델을 사용한 정확도 향상 디코딩
- **얼굴 감지**: 이미지에서 얼굴 영역 자동 감지

### API 엔드포인트

#### 1. 워터마크 임베딩
- **POST** `/embed`
- **요청**: 
  - `image`: 이미지 파일 (multipart/form-data)
  - `username`: 사용자명
  - `text`: 워터마크로 임베딩할 텍스트
- **응답**: 워터마크가 임베딩된 이미지 (PNG)

#### 2. 워터마크 디코딩
- **POST** `/decode`
- **요청**: 
  - `image`: 워터마크가 임베딩된 이미지 파일
- **응답**: 디코딩된 텍스트

#### 3. VIP 워터마크 디코딩
- **POST** `/decodeVIP`
- **요청**: 
  - `image`: 워터마크가 임베딩된 이미지 파일
- **응답**: 고급 디코딩 모델로 추출한 텍스트

#### 4. 얼굴 감지
- **POST** `/detecting`
- **요청**: 
  - `image`: 이미지 파일
- **응답**: 얼굴 감지 여부 (`ok` 또는 `no face`)

### 실행 방법

#### 1. 사전 요구사항
- Python 3.10 이상
- CUDA 지원 GPU (선택사항, CPU 모드도 가능)

#### 2. 가상 환경 설정
```bash
cd python_server

# 가상 환경이 이미 있다면 활성화
# Windows:
.\venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

#### 3. 의존성 설치 (필요한 경우)
```bash
pip install fastapi uvicorn torch torchvision pillow opencv-python qrcode ultralytics numpy
```

#### 4. 서버 실행
```bash
# 개발 모드 (자동 리로드)
uvicorn run:app --reload

# 프로덕션 모드
uvicorn run:app --host 0.0.0.0 --port 8000
```

#### 5. 서버 접속
- 기본 주소: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs` (Swagger UI)

### 모델 파일
- `embedmodel/generator.pth`: 워터마크 임베딩 생성 모델
- `decodemodel/latest_patch_decoder.pth`: 워터마크 디코딩 모델
- `yolov11l-face.pt`: 얼굴 감지 모델

### 주의사항
- 모델 파일 경로가 하드코딩되어 있을 수 있으므로, 실제 환경에 맞게 수정 필요
- GPU 사용 시 CUDA가 제대로 설치되어 있는지 확인 (`python check.py` 실행)

---

## 개발 환경 설정

### Java Server
1. JDK 17 설치 확인
   ```bash
   java -version
   ```

2. 데이터베이스 및 Redis 실행 확인
   - MariaDB: `localhost:3306`
   - Redis: `localhost:6379`

3. 설정 파일 생성
   ```bash
   cp java_server/src/main/resources/application-local.properties.example \
      java_server/src/main/resources/application-local.properties
   ```

### Python Server
1. Python 버전 확인
   ```bash
   python --version
   ```

2. 가상 환경 활성화
   ```bash
   cd python_server
   .\venv\Scripts\activate  # Windows
   ```

3. CUDA 확인 (선택사항)
   ```bash
   python check.py
   ```

---

## 라이선스

이 프로젝트의 라이선스 정보를 여기에 추가하세요.
