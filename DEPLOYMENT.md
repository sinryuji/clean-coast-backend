# Tangyuling API CI/CD 설정 가이드

## 📋 사전 준비

### 1. Docker Hub 계정

- [Docker Hub](https://hub.docker.com/) 가입
- Repository 생성: `your-username/tangyuling-api`

### 2. GitHub Secrets 설정

GitHub 저장소 → Settings → Secrets and variables → Actions에서 다음 설정:

#### 필수 Secrets

| Secret 이름       | 설명                   | 예시                         |
| ----------------- | ---------------------- | ---------------------------- |
| `DOCKER_USERNAME` | Docker Hub 사용자 이름 | `myusername`                 |
| `DOCKER_PASSWORD` | Docker Hub 액세스 토큰 | `dckr_pat_xxxxx`             |
| `SSH_PRIVATE_KEY` | 서버 접속용 SSH 개인키 | `~/.ssh/kanghyki` 파일 내용  |
| `ENV_FILE`        | 프로덕션 환경변수      | `.env.example` 참고하여 작성 |

#### ENV_FILE 예시

```env
DATABASE_URL=mysql+pymysql://root:your_password@mysql:3306/tangyuling
MYSQL_ROOT_PASSWORD=your_secure_password
MYSQL_DATABASE=tangyuling
JWT_SECRET_KEY=your-very-secure-secret-key-here
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ALAN_API_BASE_URL=https://your-alan-ai-url
ALAN_CLIENT_ID=your-client-id
DOCKER_USERNAME=your-docker-username
```

### 3. 서버 설정

#### 서버에서 실행할 명령어

```bash
# 1. Docker 설치 (Ubuntu)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# 2. 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
newgrp docker

# 3. 배포 디렉토리 생성
mkdir -p ~/tangyuling
cd ~/tangyuling

# 4. .env 파일 생성 (나중에 CI/CD가 자동으로 업데이트)
touch .env

# 5. SSH 키 설정 확인
# GitHub Actions에서 사용할 공개키를 ~/.ssh/authorized_keys에 등록되어 있는지 확인
```

## 🚀 배포 프로세스

### 자동 배포 (CI/CD)

1. **코드 푸시**

   ```bash
   git add .
   git commit -m "feat: 새로운 기능 추가"
   git push origin main
   ```

2. **GitHub Actions 자동 실행**

   - Docker 이미지 빌드
   - Docker Hub에 푸시
   - 서버에 SSH 접속
   - 최신 이미지 pull & 배포

3. **배포 확인**
   - GitHub Actions 탭에서 워크플로우 상태 확인
   - 서버: `http://hyki.me:8000/health`
   - API 문서: `http://hyki.me:8000/docs`

### 수동 배포

서버에 SSH 접속 후:

```bash
# 배포 스크립트 사용
cd ~/tangyuling
./deploy.sh

# 또는 수동으로
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

## 🔍 모니터링 및 관리

### 로그 확인

```bash
# 실시간 로그
docker-compose -f docker-compose.prod.yml logs -f api

# 최근 100줄
docker-compose -f docker-compose.prod.yml logs --tail=100 api
```

### 컨테이너 상태 확인

```bash
docker-compose -f docker-compose.prod.yml ps
```

### 컨테이너 재시작

```bash
docker-compose -f docker-compose.prod.yml restart api
```

### 데이터베이스 접속

```bash
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -p
```

### 백업

```bash
# 데이터베이스 백업
docker-compose -f docker-compose.prod.yml exec mysql mysqldump -uroot -p tangyuling > backup_$(date +%Y%m%d).sql

# 볼륨 백업
docker run --rm -v tangyuling_mysql_data:/data -v $(pwd):/backup ubuntu tar czf /backup/mysql_data_$(date +%Y%m%d).tar.gz /data
```

## 🛠️ 트러블슈팅

### 배포 실패 시

1. **GitHub Actions 로그 확인**

   - Actions 탭에서 실패한 워크플로우 클릭
   - 에러 메시지 확인

2. **서버 로그 확인**

   ```bash
   ssh -p 4242 blue@hyki.me
   cd ~/tangyuling
   docker-compose -f docker-compose.prod.yml logs --tail=100
   ```

3. **컨테이너 상태 확인**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   docker inspect tangyuling-api-prod
   ```

### 롤백

```bash
# 이전 이미지로 롤백
docker-compose -f docker-compose.prod.yml down
docker pull your-username/tangyuling-api:previous-tag
# docker-compose.prod.yml에서 이미지 태그 변경 후
docker-compose -f docker-compose.prod.yml up -d
```

## 📝 주의사항

1. **민감 정보 보안**

   - `.env` 파일은 절대 Git에 커밋하지 마세요
   - GitHub Secrets에만 저장하세요

2. **데이터베이스 백업**

   - 정기적으로 데이터베이스 백업을 수행하세요
   - 중요한 변경 전에는 반드시 백업하세요

3. **포트 설정**

   - 프로덕션에서는 8000번 포트 대신 Nginx 리버스 프록시 사용 권장
   - SSL/TLS 인증서 설정 권장

4. **모니터링**
   - 서버 리소스(CPU, 메모리, 디스크) 모니터링 설정
   - 로그 로테이션 설정

## 🔐 보안 권장사항

1. **SSH 키 관리**

   - 개인키는 안전하게 보관
   - 정기적으로 키 교체

2. **Docker Hub 토큰**

   - 비밀번호 대신 액세스 토큰 사용
   - 최소 권한 원칙 적용

3. **방화벽 설정**

   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 4242/tcp  # 커스텀 SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

4. **환경변수 보안**
   - 강력한 비밀번호 사용
   - JWT Secret은 충분히 길고 무작위로 생성
