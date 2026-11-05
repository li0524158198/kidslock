#!/usr/bin/env sh
# ============================================================
# 下载站一键部署（对应 download-site/部署说明.md 的自动化版）
# 服务器布局：/opt/kidslock/download-site（systemd 单元指向此处，
# 见 download-site/kidslock-download.service）
# 流程：release_check 卡点 → scp zip → 解压同步到服务目录 → 重启 systemd
#       → HTTP 验证 + APK 下载 md5 终验
# 用法：
#   sh scripts/deploy_site.sh                    # 默认 root@42.194.210.91
#   sh scripts/deploy_site.sh user@your-server   # 指定服务器
# 前提：ssh 免密可用；服务器有 unzip/python3/systemctl
# ============================================================
set -e
cd "$(dirname "$0")/.."

HOST=${1:-root@42.194.210.91}
PORT=29993
SITE_DIR=/opt/kidslock/download-site
ZIP=dist/kidslock-download-site.zip
APK_NAME=kidslock-v$(python -c "import re;print(re.search(r'versionName \"([^\"]+)\"', open('kidslock-src/app/build.gradle',encoding='utf-8').read()).group(1))").apk

[ -f "$ZIP" ] || { echo "[ABORT] 缺 $ZIP（先跑 python scripts/build_all.py）"; exit 1; }

echo "[0/5] 发布卡点（产物与源码一致性）..."
python qa/release_check.py >/dev/null && echo "      release_check 7/7 PASS" \
  || { echo "[ABORT] release_check 未通过，禁止发布（先跑 python scripts/build_all.py）"; exit 1; }

echo "[1/5] 上传到 $HOST ..."
scp "$ZIP" "$HOST":/opt/

echo "[2/5] 解压并同步到 $SITE_DIR ..."
ssh "$HOST" "cd /opt && unzip -oq kidslock-download-site.zip && mkdir -p $SITE_DIR && cp -rf /opt/kidslock-download/* $SITE_DIR/ && rm -rf /opt/kidslock-download && ls -l $SITE_DIR/assets/"

echo "[3/5] 安装单元并重启 kidslock-download 服务 ..."
ssh "$HOST" "cp -f $SITE_DIR/kidslock-download.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now kidslock-download >/dev/null 2>&1 || true; systemctl restart kidslock-download && sleep 1 && systemctl is-active kidslock-download"

echo "[4/5] HTTP 验证 http://$HOST:$PORT/ ..."
sleep 1
curl -s -o /dev/null -w "首页 HTTP %{http_code}\n" "http://$HOST:$PORT/"

echo "[5/5] APK 下载终验（服务器实下 md5 vs 本地 zip）..."
LOCAL_MD5=$(python -c "import zipfile,hashlib;print(hashlib.md5(zipfile.ZipFile('$ZIP').read('kidslock-download/assets/$APK_NAME')).hexdigest())")
REMOTE_MD5=$(curl -sf "http://$HOST:$PORT/assets/$APK_NAME" | md5sum | cut -d' ' -f1)
echo "      本地 $LOCAL_MD5"
echo "      服务器 $REMOTE_MD5"
if [ "$LOCAL_MD5" != "$REMOTE_MD5" ]; then
  echo "[ABORT] APK md5 不一致：服务目录/端口可能被旧进程占用，查 journalctl -u kidslock-download -f"
  exit 1
fi
echo "APK 终验一致。部署完成：http://$HOST:$PORT/"
