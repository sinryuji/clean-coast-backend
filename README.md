# 제주 해양환경 예측 서비스 깨끗海

제주도 주변 해양환경 데이터를 시각화하는 웹 애플리케이션입니다.

<img width="1280" height="682" alt="image" src="https://github.com/user-attachments/assets/6861280a-3cea-4083-9f25-ff3b2555d5f1" />

## 설치

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

## 실행

```bash
uvicorn main:app --reload
```

서버는 http://127.0.0.1:8000 에서 실행됩니다.

## API 문서

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
