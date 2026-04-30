# Codex Browser Context Bridge

This repo includes a small local bridge that approximates VS Code Copilot's
"send browser element to chat" workflow for Codex.

The basic flow is:

1. Run a local Python receiver from this repo.
2. Inject the capture script into the browser page you are inspecting.
3. Click an element.
4. The bridge writes `.codex/browser-context/latest.md`.
5. Ask Codex to use that file as UI context.

## Why This Shape

The Copilot integrated-browser command appears to be wired into VS Code and
Copilot-specific chat internals. That private route is likely brittle and may
not expose a clean way for another extension to push context directly into the
Codex chat input.

This bridge copies the useful part of the behavior at a more stable boundary:
the browser page can describe a selected DOM element, and Codex can read files
from the workspace. The result is less magical than Copilot's direct chat
handoff, but it is transparent, editable, and independent of private VS Code
extension APIs.

## Files

- `tools/browser_context_bridge.py`: a standard-library HTTP server that accepts
  element captures and writes Markdown files.
- `tools/capture_element_context.js`: a browser-side overlay. Hover an element,
  click it, and the script sends context to the bridge.
- `.codex/browser-context/latest.md`: the newest generated capture. This path is
  ignored by git.
- `.codex/browser-context/capture-YYYYMMDD-HHMMSS.md`: timestamped capture
  history, also ignored by git.

## Start The Bridge

From the repo root:

```powershell
py -3.13 tools/browser_context_bridge.py
```

If you are not using the Windows Python launcher:

```powershell
python tools/browser_context_bridge.py
```

The server listens on:

```text
http://127.0.0.1:4755
```

You can change the port if needed:

```powershell
py -3.13 tools/browser_context_bridge.py --port 4760
```

If you change the port, set this in the browser before loading the capture
script:

```javascript
window.CODEX_ELEMENT_BRIDGE_URL = "http://127.0.0.1:4760/capture";
```

## Inject The Browser Capture Script

Open the page you want to inspect in the VS Code integrated browser, then open
that page's devtools console and run:

```javascript
fetch("http://127.0.0.1:4755/capture-element-context.js").then(r => r.text()).then(eval)
```

For VS Code webviews, the command palette command is usually
`Developer: Open Webview Developer Tools`. Other integrated browser extensions
may expose their own devtools command.

An overlay appears on the page. Hover the target element and click it. The click
is intercepted so the page action does not fire while capturing.

Press `Esc` or click `Exit` to remove the overlay.

## Use The Capture With Codex

After clicking an element, use a prompt like:

```text
Use .codex/browser-context/latest.md as browser context. Fix the selected UI
element with the smallest code change that preserves unrelated behavior.
```

The generated Markdown includes:

- page URL, title, viewport, and scroll position
- selected element selector, text, attributes, bounding box, and outer HTML
- selected computed CSS properties
- ancestors, previous siblings, next siblings, and nearby text
- referenced image/video/background URLs when available
- the raw JSON capture

## Clipboard Fallback

If the bridge is not running or the browser blocks the request, the capture
script tries to copy a Markdown version of the capture to the clipboard. In that
case, paste the clipboard contents into Codex manually.

## Limitations

- The script cannot capture browser screenshots. It captures DOM, CSS, layout,
  and text context.
- Cross-origin browser policies can still block some resource details.
- Shadow DOM content may be incomplete depending on how the component exposes
  its internals.
- Directly injecting into the Codex chat UI would require Codex or VS Code to
  expose a stable command/API for that. This bridge intentionally avoids private
  UI automation.

## Design Reasoning

The most reliable integration point is the workspace filesystem. Codex already
understands local files, while a web page can safely POST structured JSON to a
loopback HTTP server. The Python server keeps dependencies at zero and fits this
repo's current Python setup. The JavaScript capture overlay keeps the browser
side portable: it can be loaded from the local bridge, pasted into a console, or
adapted into a bookmarklet later.

The output is Markdown rather than only JSON because it is easier to scan in
chat and still preserves the full raw payload for exact debugging.
