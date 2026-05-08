#!/bin/bash
# EC2 t2.micro (Ubuntu 24.04) 초기 세팅 스크립트
# 사용법: ssh ubuntu@<EC2_IP> 'bash -s' < setup_ec2.sh

set -euo pipefail

APP_DIR="/home/ubuntu/youth-ht"
REPO="https://github.com/LeeJaeHaeng/youth-ht.git"
SERVICE="youth-ht"

echo "=== 1. 패키지 업데이트 ==="
sudo apt-get update -qq
sudo apt-get install -y -qq python3.12 python3.12-venv python3.12-dev git curl

echo "=== 2. 소스 클론 ==="
if [ -d "$APP_DIR" ]; then
  cd "$APP_DIR" && git pull
else
  git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"

echo "=== 3. 가상환경 + 의존성 ==="
python3.12 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
# torch 제외 (GRU 추론 미사용, 예측값 parquet만 사용)
grep -v "^torch" requirements.txt > /tmp/req_no_torch.txt
.venv/bin/pip install --quiet -r /tmp/req_no_torch.txt

echo "=== 4. data/processed 디렉토리 생성 ==="
mkdir -p data/processed data/raw

echo "=== 5. systemd 서비스 등록 ==="
sudo tee /etc/systemd/system/${SERVICE}.service > /dev/null <<EOF
[Unit]
Description=Youth HT FastAPI
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE}
sudo systemctl restart ${SERVICE}

echo "=== 완료 ==="
echo "서비스 상태: sudo systemctl status ${SERVICE}"
echo "헬스체크: curl http://localhost:8000/healthz"
