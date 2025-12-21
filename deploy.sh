#!/bin/bash

# Tangyuling API 배포 스크립트
# 서버에서 수동으로 배포할 때 사용

set -e

echo "🚀 Tangyuling API 배포 시작..."

# DOCKER_USERNAME 환경 변수 확인
if [ -z "$DOCKER_USERNAME" ]; then
    echo "❌ DOCKER_USERNAME 환경 변수가 설정되지 않았습니다."
    echo "사용법: DOCKER_USERNAME=your-username ./deploy.sh"
    exit 1
fi

# Docker Hub 로그인 확인
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker가 실행되고 있지 않습니다."
    exit 1
fi

# 배포 디렉토리로 이동
cd ~/tangyuling

# 최신 이미지 pull
echo "📥 최신 Docker 이미지 다운로드 중..."
docker compose -f docker-compose.prod.yml pull

# 기존 컨테이너 중지
echo "🛑 기존 컨테이너 중지 중..."
docker compose -f docker-compose.prod.yml down

# 새 컨테이너 시작
echo "▶️  새 컨테이너 시작 중..."
docker compose -f docker-compose.prod.yml up -d

# 컨테이너 상태 확인
echo "✅ 컨테이너 상태 확인..."
sleep 5
docker compose -f docker-compose.prod.yml ps

# 로그 확인
echo "📋 최근 로그 확인..."
docker compose -f docker-compose.prod.yml logs --tail=30 api

# 헬스체크
echo "🏥 API 헬스체크..."
sleep 3
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 배포 완료! API가 정상적으로 실행 중입니다."
else
    echo "⚠️  API 헬스체크 실패. 로그를 확인하세요."
    docker-compose -f docker-compose.prod.yml logs --tail=50 api
    exit 1
fi

# 사용하지 않는 이미지 정리
echo "🧹 사용하지 않는 이미지 정리 중..."
docker image prune -af

echo "✨ 배포 완료!"
