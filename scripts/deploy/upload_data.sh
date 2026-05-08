#!/bin/bash
# 로컬 → EC2 데이터 파일 업로드 스크립트
# 사용법: bash upload_data.sh <EC2_IP> <PEM_KEY_PATH>
# 예시:  bash upload_data.sh 13.125.x.x ~/.ssh/youth-ht.pem

set -euo pipefail

EC2_IP="${1:?EC2 IP를 첫 번째 인자로 입력하세요}"
PEM="${2:?PEM 키 경로를 두 번째 인자로 입력하세요}"
REMOTE="ubuntu@${EC2_IP}"
APP_DIR="/home/ubuntu/youth-ht"

echo "=== .env 업로드 ==="
scp -i "$PEM" .env "${REMOTE}:${APP_DIR}/.env"

echo "=== data/processed/ 업로드 ==="
ssh -i "$PEM" "${REMOTE}" "mkdir -p ${APP_DIR}/data/processed"
scp -i "$PEM" data/processed/*.parquet "${REMOTE}:${APP_DIR}/data/processed/" 2>/dev/null || true

echo "=== docs/work_clusters.csv 업로드 ==="
ssh -i "$PEM" "${REMOTE}" "mkdir -p ${APP_DIR}/docs"
scp -i "$PEM" docs/work_clusters.csv "${REMOTE}:${APP_DIR}/docs/" 2>/dev/null || true

echo "=== 서비스 재시작 ==="
ssh -i "$PEM" "${REMOTE}" "sudo systemctl restart youth-ht && sleep 2 && curl -s http://localhost:8000/healthz"

echo "=== 완료 ==="
echo "API 주소: http://${EC2_IP}:8000"
