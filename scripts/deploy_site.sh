#!/usr/bin/env sh
# ============================================================
# 下载站一键部署（对应 download-site/部署说明.md 的自动化版）
# 流程：release_check 卡点 → scp zip → 服务器解压替换 → 重启 systemd → HTTP 验证
# 用法：
#   sh scripts/deploy_site.sh                    # 默认 root@192.168.230.100
#   sh scripts/deploy_site.sh user@your-server   # 指定服务器
# 前提：ssh 免密可用（~/.ssh/config 已配 IdentityFile）；服务器有 unzip/python3
# ============================================================
set -e
cd "$(dirname "$0")/.."

HOST=${1:-root@192.168.230.100}
PORT=29993
ZIP=dist/kidslock-download-site.zip

[ -f "$ZIP" ] || { echo "[ABORT] 缺 $ZIP（先跑 python scripts/build_all.py）"; exit 1; }

echo "[0/4] 发布卡点（产物与源码一致性）..."
python qa/release_check.py >/dev/null && echo "      release_check 7/7 PASS" \
  || { echo "[ABORT] release_check 未通过，禁止发布（先跑 python scripts/build_all.py）"; exit 1; }

echo "[1/4] 上传到 $HOST ..."
scp "$ZIP" "$HOST":/opt/

echo "[2/4] 服务器解压替换 /opt/kidslock-download ..."
ssh "$HOST" "cd /opt && unzip -oq kidslock-download-site.zip && ls -l /opt/kidslock-download/assets/"

echo "[3/4] 重启 kidslock-download 服务 ..."
ssh "$HOST" "cp -f /opt/kidslock-download/kidslock-download.service /etc/systemd/system/ 2>/dev/null || true; systemctl daemon-reload; systemctl enable --now kidslock-download >/dev/null 2>&1 || true; systemctl restart kidslock-download; sleep 1; systemctl is-active kidslock-download"

echo "[4/4] HTTP 验证 http://$HOST:$PORT/ ..."
sleep 1
curl -s -o /dev/null -w "HTTP %{http_code}\n" "http://$HOST:$PORT/" || {
  echo "[WARN] HTTP 验证失败：检查端口放行（server.py 默认 $PORT）与服务日志 journalctl -u kidslock-download -f"
  exit 1
}

echo "部署完成：$HOST:$PORT"
