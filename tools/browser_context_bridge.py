from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4755
DEFAULT_OUTPUT_DIR = ROOT / ".codex" / "browser-context"
CAPTURE_SCRIPT_PATH = Path(__file__).with_name("capture_element_context.js")
MAX_BODY_BYTES = 5 * 1024 * 1024


def truncate(value: Any, limit: int = 20000) -> str:
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n\n...[truncated {len(text) - limit} characters]"


def code_fence(language: str, content: Any) -> str:
    text = truncate(content)
    return f"```{language}\n{text.replace('```', '`` `')}\n```"


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def field(value: Any, fallback: str = "") -> str:
    text = "" if value is None else str(value)
    return text if text else fallback


def render_node_summary(node: dict[str, Any]) -> str:
    pieces = [field(node.get("tagName"), "element")]
    if node.get("id"):
        pieces.append(f"#{node['id']}")
    if node.get("className"):
        classes = ".".join(str(node["className"]).split())
        if classes:
            pieces.append(f".{classes}")
    selector = field(node.get("selector"))
    text = field(node.get("text")).replace("\n", " ")
    text = truncate(text, 160)
    summary = "".join(pieces)
    if selector:
        summary += f" | selector: `{selector}`"
    if text:
        summary += f" | text: {text}"
    return f"- {summary}"


def render_markdown(payload: dict[str, Any], saved_at: dt.datetime) -> str:
    page = payload.get("page") or {}
    element = payload.get("element") or {}
    rect = element.get("rect") or {}
    computed = element.get("computedStyles") or {}
    ancestors = payload.get("ancestors") or []
    previous_siblings = payload.get("previousSiblings") or []
    next_siblings = payload.get("nextSiblings") or []
    resources = payload.get("resources") or []

    page_title = field(page.get("title"), "Untitled page")
    page_url = field(page.get("url"), "unknown URL")
    selector = field(element.get("selector"), "unknown selector")
    captured_at = field(payload.get("capturedAt"), saved_at.isoformat())

    lines = [
        "# Browser Element Context",
        "",
        "Use this capture as concrete UI context for Codex. It includes the selected",
        "element, its nearby DOM, layout metrics, and the most relevant computed CSS.",
        "",
        "Suggested prompt:",
        "",
        "> Use this browser capture to inspect the referenced UI element and make the",
        "> smallest code change needed. Preserve unrelated behavior.",
        "",
        "## Capture",
        "",
        f"- Captured by browser: `{captured_at}`",
        f"- Saved by bridge: `{saved_at.isoformat()}`",
        f"- Page title: {page_title}",
        f"- Page URL: {page_url}",
        f"- Selector: `{selector}`",
        f"- Viewport: `{compact_json(page.get('viewport') or {})}`",
        f"- Scroll: `{compact_json(page.get('scroll') or {})}`",
        "",
        "## Selected Element",
        "",
        f"- Tag: `{field(element.get('tagName'), 'unknown')}`",
        f"- ID: `{field(element.get('id'), '')}`",
        f"- Classes: `{field(element.get('className'), '')}`",
        f"- Role: `{field(element.get('role'), '')}`",
        f"- Accessible label: `{field(element.get('ariaLabel'), '')}`",
        f"- Bounding box: `{compact_json(rect)}`",
        "",
        "Visible text:",
        "",
        code_fence("text", element.get("text") or ""),
        "",
        "Outer HTML:",
        "",
        code_fence("html", element.get("outerHTML") or ""),
        "",
        "Attributes:",
        "",
        code_fence("json", element.get("attributes") or {}),
        "",
        "Computed styles:",
        "",
        code_fence("json", computed),
    ]

    if ancestors:
        lines.extend(
            [
                "",
                "## Ancestors",
                "",
                *[render_node_summary(node) for node in ancestors],
            ]
        )

    if previous_siblings or next_siblings:
        lines.extend(["", "## Nearby Siblings", ""])
        if previous_siblings:
            lines.extend(["Previous siblings:", "", *[render_node_summary(node) for node in previous_siblings]])
        if next_siblings:
            if previous_siblings:
                lines.append("")
            lines.extend(["Next siblings:", "", *[render_node_summary(node) for node in next_siblings]])

    nearby_text = field(payload.get("nearbyText"))
    if nearby_text:
        lines.extend(["", "## Nearby Text", "", code_fence("text", nearby_text)])

    if resources:
        lines.extend(["", "## Referenced Media", "", code_fence("json", resources)])

    lines.extend(["", "## Raw Capture", "", code_fence("json", payload), ""])
    return "\n".join(lines)


def write_capture(payload: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    saved_at = dt.datetime.now().astimezone()
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(payload, saved_at)
    timestamp = saved_at.strftime("%Y%m%d-%H%M%S")
    capture_path = output_dir / f"capture-{timestamp}.md"
    latest_path = output_dir / "latest.md"
    capture_path.write_text(markdown, encoding="utf-8")
    latest_path.write_text(markdown, encoding="utf-8")
    return capture_path, latest_path


class BridgeServer(ThreadingHTTPServer):
    output_dir: Path
    capture_script_path: Path


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "CodexBrowserContextBridge/0.1"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_text(self.index_html(), content_type="text/html; charset=utf-8")
            return
        if path == "/capture-element-context.js":
            script_path = self.typed_server.capture_script_path
            if not script_path.exists():
                self.send_error(404, "capture_element_context.js not found")
                return
            self.send_text(script_path.read_text(encoding="utf-8"), content_type="text/javascript; charset=utf-8")
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/capture":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            self.send_error(400, "Missing request body")
            return
        if length > MAX_BODY_BYTES:
            self.send_error(413, "Capture is too large")
            return

        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.send_error(400, f"Invalid JSON: {exc}")
            return
        if not isinstance(payload, dict):
            self.send_error(400, "Capture payload must be a JSON object")
            return

        capture_path, latest_path = write_capture(payload, self.typed_server.output_dir)
        response = {
            "ok": True,
            "capturePath": str(capture_path),
            "latestPath": str(latest_path),
        }
        self.send_json(response)
        print(f"Saved browser context: {latest_path}", flush=True)

    @property
    def typed_server(self) -> BridgeServer:
        return self.server  # type: ignore[return-value]

    def send_json(self, value: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, value: str, content_type: str = "text/plain; charset=utf-8", status: int = 200) -> None:
        body = value.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def index_html(self) -> str:
        host, port = self.server.server_address[:2]
        script_url = f"http://{host}:{port}/capture-element-context.js"
        escaped_script_url = html.escape(script_url, quote=True)
        return f"""<!doctype html>
<meta charset="utf-8">
<title>Codex Browser Context Bridge</title>
<style>
body {{ font: 14px/1.5 system-ui, sans-serif; margin: 2rem; max-width: 760px; }}
code, pre {{ background: #f4f4f4; border-radius: 4px; }}
code {{ padding: 0.1rem 0.25rem; }}
pre {{ padding: 1rem; overflow: auto; }}
</style>
<h1>Codex Browser Context Bridge</h1>
<p>The bridge is running. Captures will be written to <code>{html.escape(str(self.typed_server.output_dir))}</code>.</p>
<p>Paste this into the target browser console to install the capture overlay:</p>
<pre><code>fetch("{escaped_script_url}").then(r =&gt; r.text()).then(eval)</code></pre>
"""

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Receive selected browser element context and write Markdown for Codex.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind. Default: {DEFAULT_HOST}")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind. Default: {DEFAULT_PORT}")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for generated captures. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--capture-script",
        type=Path,
        default=CAPTURE_SCRIPT_PATH,
        help=f"Browser capture script to serve. Default: {CAPTURE_SCRIPT_PATH}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = BridgeServer((args.host, args.port), BridgeHandler)
    server.output_dir = args.output_dir.resolve()
    server.capture_script_path = args.capture_script.resolve()
    print(f"Codex browser context bridge listening on http://{args.host}:{args.port}", flush=True)
    print(f"Writing captures to {server.output_dir}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping bridge.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
