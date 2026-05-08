#!/bin/bash
# 코드 업데이트 + 서비스 재시작 (배포 후 업데이트용)
# EC2에서 직접 실행: bash ~/youth-ht/scripts/deploy/deploy.sh

set -euo pipefail

cd /home/ubuntu/youth-ht
git pull origin master
.venv/bin/pip install --quiet -r <(grep -v "^torch" requirements.txt)
sudo systemctl restart youth-ht
sleep 2
curl -s http://localhost:8000/healthz
echo ""
echo "배포 완료"
