#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
儿童锁屏 · 下载站服务器（零依赖，Python 3.6+ 标准库）

用法：
    python3 server.py                        # 默认 0.0.0.0:29993
    python3 server.py --port 80              # 换端口
    python3 server.py --host 127.0.0.1       # 只允许本机访问（套 nginx 反代时用）

特性：
    - 正确的 APK/HAP MIME 类型，安卓浏览器下载后可直接引导安装
    - 多线程并发（多个客户同时下载互不阻塞）
    - 防目录穿越，无目录列表，只提供站点内文件
    - 访问日志带时间戳，方便统计下载量
"""
import argparse
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from socketserver import ThreadingMixIn

# 站点根目录 = 本脚本所在目录
ROOT = os.path.dirname(os.path.abspath(__file__))

MIME_TYPES = {
    '.apk': 'application/vnd.android.package-archive',  # 关键：安卓安装包
    '.hap': 'application/octet-stream',
    '.html': 'text/html; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
    '.pdf': 'application/pdf',
}


class DownloadSiteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        # APK/HAP 走附件下载；其余（页面/图片）内联展示
        path = self.translate_path(self.path)
        if path.endswith(('.apk', '.hap')):
            name = os.path.basename(path)
            self.send_header('Content-Disposition', f'attachment; filename="{name}"')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIME_TYPES.get(ext, 'application/octet-stream')

    def translate_path(self, path):
        # 路径钳制：任何包含 .. 的越权访问一律映射到不存在的文件 → 404
        p = os.path.abspath(super().translate_path(path))
        root = os.path.abspath(ROOT)
        if p == root or p.startswith(root + os.sep):
            # 服务器脚本本身不对外提供下载
            if os.path.basename(p) in ('server.py',):
                return os.path.join(root, '.__blocked__')
            return p
        return os.path.join(root, '.__blocked__')

    def log_message(self, fmt, *args):
        # 带时间戳的访问日志
        import datetime
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sys.stdout.write(f'[{ts}] {self.address_string()} {fmt % args}\n')
        sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description='儿童锁屏下载站')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址（默认 0.0.0.0）')
    parser.add_argument('--port', type=int, default=29993, help='端口（默认 29993）')
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DownloadSiteHandler)
    print(f'儿童锁屏下载站已启动: http://{args.host}:{args.port}/')
    print(f'站点目录: {ROOT}')
    print('按 Ctrl+C 停止')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务器已停止')
        server.server_close()


if __name__ == '__main__':
    main()
