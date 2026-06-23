"""Run the True Monad local workbench on http://127.0.0.1:8051."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from true_monad import (
    PactError, archive_round, create_instruction, delete_instruction, emit_trigger,
    respond_to_interaction, save_instruction, snapshot,
)


STATIC = Path(__file__).resolve().parent / "static"


class Handler(BaseHTTPRequestHandler):
    server_version = "TrueMonad/0.1"

    def log_message(self, fmt, *args):
        sys.stdout.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 2 * 1024 * 1024:
            raise PactError("请求内容超过 2MB")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except (json.JSONDecodeError, UnicodeError):
            raise PactError("请求不是有效的 UTF-8 JSON")

    def _static(self, relative):
        target = (STATIC / relative).resolve()
        if STATIC.resolve() not in target.parents and target != STATIC.resolve():
            self.send_error(404)
            return
        if not target.is_file():
            self.send_error(404)
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/snapshot":
            return self._json(200, snapshot())
        if path == "/api/health":
            return self._json(200, {"status": "ok"})
        if path == "/":
            return self._static("index.html")
        if path.startswith("/static/"):
            return self._static(unquote(path[len("/static/"):]))
        self.send_error(404)

    def do_PUT(self):
        try:
            path = urlparse(self.path).path
            if not path.startswith("/api/instructions/"):
                return self._json(404, {"error": "接口不存在"})
            body = self._body()
            result = save_instruction(unquote(path.split("/")[-1]), body.get("content", ""))
            self._json(200, result)
        except PactError as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            self._json(500, {"error": "服务错误：%s" % exc})

    def do_DELETE(self):
        try:
            path = urlparse(self.path).path
            if not path.startswith("/api/instructions/"):
                return self._json(404, {"error": "接口不存在"})
            delete_instruction(unquote(path.split("/")[-1]))
            self._json(200, {"deleted": True})
        except PactError as exc:
            self._json(400, {"error": str(exc)})

    def do_POST(self):
        try:
            path = urlparse(self.path).path
            body = self._body()
            if path == "/api/instructions":
                result = create_instruction(body.get("kind", "I"), body.get("content", ""))
            elif path == "/api/interactions/respond":
                result = respond_to_interaction(body.get("kind", ""), body.get("id", ""), body.get("content", ""))
            elif path == "/api/trigger":
                result = emit_trigger(str(body.get("signal", "1")))
            elif path == "/api/archive":
                if body.get("confirm") is not True:
                    raise PactError("归档操作需要明确确认")
                result = archive_round()
            else:
                return self._json(404, {"error": "接口不存在"})
            self._json(200, result)
        except PactError as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            self._json(500, {"error": "服务错误：%s" % exc})


def main():
    parser = argparse.ArgumentParser(description="True Monad local workbench")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8051)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("True Monad 工作台：http://%s:%d" % (args.host, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
