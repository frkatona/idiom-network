(function () {
  "use strict";

  var existing = window.__codexElementCapture;
  if (existing && typeof existing.start === "function") {
    existing.start();
    return;
  }

  var BRIDGE_URL = window.CODEX_ELEMENT_BRIDGE_URL || "http://127.0.0.1:4755/capture";
  var MAX_TEXT = 4000;
  var MAX_HTML = 12000;
  var MAX_NEARBY_TEXT = 6000;
  var STYLE_PROPS = [
    "display",
    "position",
    "top",
    "right",
    "bottom",
    "left",
    "width",
    "height",
    "box-sizing",
    "margin",
    "padding",
    "border",
    "border-radius",
    "font",
    "font-size",
    "font-weight",
    "line-height",
    "letter-spacing",
    "color",
    "background",
    "background-color",
    "opacity",
    "z-index",
    "overflow",
    "white-space",
    "text-align",
    "align-items",
    "justify-content",
    "grid-template-columns",
    "grid-template-rows",
    "gap",
    "transform"
  ];

  var overlay = null;
  var toolbar = null;
  var styleTag = null;
  var active = false;
  var hoveredElement = null;

  function truncate(value, limit) {
    var text = value == null ? "" : String(value);
    if (text.length <= limit) {
      return text;
    }
    return text.slice(0, limit) + "\n\n...[truncated " + (text.length - limit) + " characters]";
  }

  function cleanText(value, limit) {
    return truncate(String(value || "").replace(/\s+/g, " ").trim(), limit);
  }

  function roundNumber(value) {
    return Math.round(Number(value || 0) * 100) / 100;
  }

  function escapeSelectorPart(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(value);
    }
    return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  function rectFor(element) {
    var rect = element.getBoundingClientRect();
    return {
      x: roundNumber(rect.x),
      y: roundNumber(rect.y),
      width: roundNumber(rect.width),
      height: roundNumber(rect.height),
      top: roundNumber(rect.top),
      right: roundNumber(rect.right),
      bottom: roundNumber(rect.bottom),
      left: roundNumber(rect.left)
    };
  }

  function selectorFor(element) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) {
      return "";
    }

    if (element.id) {
      var idSelector = "#" + escapeSelectorPart(element.id);
      try {
        if (document.querySelectorAll(idSelector).length === 1) {
          return idSelector;
        }
      } catch (error) {}
    }

    var parts = [];
    var current = element;
    while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.documentElement) {
      var tag = current.tagName.toLowerCase();
      var part = tag;
      if (current.id) {
        part += "#" + escapeSelectorPart(current.id);
        parts.unshift(part);
        break;
      }

      var classes = Array.prototype.slice.call(current.classList || [])
        .filter(Boolean)
        .slice(0, 3);
      if (classes.length) {
        part += "." + classes.map(escapeSelectorPart).join(".");
      }

      var sameTagIndex = 1;
      var sameTagCount = 0;
      var sibling = current.parentElement ? current.parentElement.firstElementChild : null;
      while (sibling) {
        if (sibling.tagName === current.tagName) {
          sameTagCount += 1;
          if (sibling === current) {
            sameTagIndex = sameTagCount;
          }
        }
        sibling = sibling.nextElementSibling;
      }
      if (sameTagCount > 1) {
        part += ":nth-of-type(" + sameTagIndex + ")";
      }

      parts.unshift(part);
      var candidate = parts.join(" > ");
      try {
        if (document.querySelector(candidate) === element) {
          return candidate;
        }
      } catch (error) {}
      current = current.parentElement;
      if (parts.length >= 8) {
        break;
      }
    }
    return parts.join(" > ");
  }

  function attributesFor(element) {
    var attributes = {};
    Array.prototype.forEach.call(element.attributes || [], function (attribute) {
      attributes[attribute.name] = truncate(attribute.value, 1000);
    });
    return attributes;
  }

  function computedStylesFor(element) {
    var styles = {};
    var computed = window.getComputedStyle(element);
    STYLE_PROPS.forEach(function (property) {
      styles[property] = computed.getPropertyValue(property);
    });
    return styles;
  }

  function summarizeElement(element, options) {
    var includeOuterHTML = options && options.includeOuterHTML;
    var includeComputed = options && options.includeComputed;
    var summary = {
      tagName: element.tagName ? element.tagName.toLowerCase() : "",
      id: element.id || "",
      className: element.className && typeof element.className === "string" ? element.className : "",
      selector: selectorFor(element),
      role: element.getAttribute ? element.getAttribute("role") || "" : "",
      ariaLabel: element.getAttribute ? element.getAttribute("aria-label") || "" : "",
      title: element.getAttribute ? element.getAttribute("title") || "" : "",
      text: cleanText(element.innerText || element.textContent || "", MAX_TEXT),
      attributes: attributesFor(element),
      rect: rectFor(element)
    };

    if (includeOuterHTML) {
      summary.outerHTML = truncate(element.outerHTML || "", MAX_HTML);
    }
    if (includeComputed) {
      summary.computedStyles = computedStylesFor(element);
    }
    return summary;
  }

  function collectAncestors(element) {
    var ancestors = [];
    var current = element.parentElement;
    while (current && current !== document.body.parentElement && ancestors.length < 8) {
      ancestors.push(summarizeElement(current, { includeOuterHTML: false, includeComputed: false }));
      current = current.parentElement;
    }
    return ancestors;
  }

  function collectSiblings(element, direction) {
    var siblings = [];
    var current = direction === "previous" ? element.previousElementSibling : element.nextElementSibling;
    while (current && siblings.length < 4) {
      siblings.push(summarizeElement(current, { includeOuterHTML: false, includeComputed: false }));
      current = direction === "previous" ? current.previousElementSibling : current.nextElementSibling;
    }
    return siblings;
  }

  function collectNearbyText(element) {
    var container = element.closest("main, section, article, aside, nav, header, footer, form, [role='dialog'], [role='region']");
    if (!container && element.parentElement) {
      container = element.parentElement;
    }
    return cleanText(container ? container.innerText || container.textContent || "" : "", MAX_NEARBY_TEXT);
  }

  function collectResources(element) {
    var resources = [];
    var seen = {};

    function add(kind, url, selector) {
      if (!url || seen[kind + ":" + url]) {
        return;
      }
      seen[kind + ":" + url] = true;
      resources.push({ kind: kind, url: url, selector: selector || "" });
    }

    Array.prototype.forEach.call(element.querySelectorAll ? element.querySelectorAll("img, source, video") : [], function (node) {
      add(node.tagName.toLowerCase(), node.currentSrc || node.src || node.getAttribute("src"), selectorFor(node));
      add("srcset", node.getAttribute("srcset"), selectorFor(node));
    });

    [element].concat(Array.prototype.slice.call(element.querySelectorAll ? element.querySelectorAll("*") : [])).forEach(function (node) {
      var backgroundImage = window.getComputedStyle(node).getPropertyValue("background-image");
      var matches = backgroundImage.match(/url\(["']?([^"')]+)["']?\)/g) || [];
      matches.forEach(function (match) {
        add("background-image", match.replace(/^url\(["']?/, "").replace(/["']?\)$/, ""), selectorFor(node));
      });
    });

    return resources.slice(0, 24);
  }

  function buildPayload(element) {
    return {
      source: "codex-browser-context-capture",
      version: 1,
      capturedAt: new Date().toISOString(),
      bridgeUrl: BRIDGE_URL,
      page: {
        title: document.title || "",
        url: location.href,
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight,
          devicePixelRatio: window.devicePixelRatio || 1
        },
        scroll: {
          x: roundNumber(window.scrollX),
          y: roundNumber(window.scrollY)
        },
        userAgent: navigator.userAgent
      },
      element: summarizeElement(element, { includeOuterHTML: true, includeComputed: true }),
      ancestors: collectAncestors(element),
      previousSiblings: collectSiblings(element, "previous"),
      nextSiblings: collectSiblings(element, "next"),
      nearbyText: collectNearbyText(element),
      resources: collectResources(element)
    };
  }

  function fallbackMarkdown(payload) {
    return [
      "# Browser Element Context",
      "",
      "The local Codex bridge was not reachable, so the browser copied this capture to the clipboard.",
      "",
      "Use this capture to inspect the referenced UI element and make the smallest code change needed.",
      "",
      "```json",
      JSON.stringify(payload, null, 2),
      "```"
    ].join("\n");
  }

  function setStatus(message) {
    if (!toolbar) {
      return;
    }
    var status = toolbar.querySelector("[data-codex-capture-status]");
    if (status) {
      status.textContent = message;
    }
  }

  async function deliver(payload) {
    setStatus("Sending context to Codex bridge...");
    try {
      var response = await fetch(BRIDGE_URL, {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        throw new Error("Bridge returned HTTP " + response.status);
      }
      var result = await response.json();
      setStatus("Saved to " + (result.latestPath || ".codex/browser-context/latest.md"));
      console.log("Codex element context saved", result);
    } catch (error) {
      console.warn("Codex bridge unavailable; copying capture to clipboard instead.", error);
      try {
        await navigator.clipboard.writeText(fallbackMarkdown(payload));
        setStatus("Bridge unavailable. Context copied to clipboard.");
      } catch (clipboardError) {
        setStatus("Bridge unavailable. Capture logged to console.");
        console.log("Codex element context", payload);
      }
    }
  }

  function installUi() {
    styleTag = document.createElement("style");
    styleTag.setAttribute("data-codex-capture", "true");
    styleTag.textContent = [
      ".codex-capture-overlay {",
      "  position: fixed;",
      "  z-index: 2147483646;",
      "  pointer-events: none;",
      "  border: 2px solid #0ea5e9;",
      "  background: rgba(14, 165, 233, 0.12);",
      "  box-shadow: 0 0 0 99999px rgba(15, 23, 42, 0.10);",
      "}",
      ".codex-capture-toolbar {",
      "  position: fixed;",
      "  z-index: 2147483647;",
      "  top: 12px;",
      "  left: 50%;",
      "  transform: translateX(-50%);",
      "  display: flex;",
      "  gap: 10px;",
      "  align-items: center;",
      "  max-width: min(780px, calc(100vw - 24px));",
      "  padding: 8px 10px;",
      "  border: 1px solid rgba(15, 23, 42, 0.20);",
      "  border-radius: 6px;",
      "  background: #ffffff;",
      "  color: #0f172a;",
      "  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.20);",
      "  font: 12px/1.35 system-ui, -apple-system, Segoe UI, sans-serif;",
      "}",
      ".codex-capture-toolbar button {",
      "  border: 1px solid rgba(15, 23, 42, 0.24);",
      "  border-radius: 4px;",
      "  background: #f8fafc;",
      "  color: #0f172a;",
      "  cursor: pointer;",
      "  font: inherit;",
      "  padding: 3px 7px;",
      "}",
      ".codex-capture-toolbar [data-codex-capture-status] {",
      "  overflow: hidden;",
      "  text-overflow: ellipsis;",
      "  white-space: nowrap;",
      "}"
    ].join("\n");
    document.documentElement.appendChild(styleTag);

    overlay = document.createElement("div");
    overlay.className = "codex-capture-overlay";
    document.documentElement.appendChild(overlay);

    toolbar = document.createElement("div");
    toolbar.className = "codex-capture-toolbar";
    toolbar.innerHTML = '<strong>Codex capture</strong><span data-codex-capture-status>Hover an element, click to capture, Esc to exit.</span><button type="button">Exit</button>';
    toolbar.querySelector("button").addEventListener("click", stop);
    document.documentElement.appendChild(toolbar);
  }

  function removeUi() {
    if (overlay) {
      overlay.remove();
      overlay = null;
    }
    if (toolbar) {
      toolbar.remove();
      toolbar = null;
    }
    if (styleTag) {
      styleTag.remove();
      styleTag = null;
    }
  }

  function isCaptureUi(target) {
    return target && (target === overlay || target === toolbar || (toolbar && toolbar.contains(target)));
  }

  function updateOverlay(element) {
    if (!overlay || !element || isCaptureUi(element)) {
      return;
    }
    hoveredElement = element;
    var rect = element.getBoundingClientRect();
    overlay.style.left = rect.left + "px";
    overlay.style.top = rect.top + "px";
    overlay.style.width = rect.width + "px";
    overlay.style.height = rect.height + "px";
  }

  function onMouseMove(event) {
    if (!isCaptureUi(event.target)) {
      updateOverlay(event.target);
    }
  }

  function onClick(event) {
    if (isCaptureUi(event.target)) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    var element = event.target || hoveredElement;
    if (element) {
      deliver(buildPayload(element));
    }
  }

  function onKeyDown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      stop();
    }
  }

  function start() {
    if (active) {
      setStatus("Hover an element, click to capture, Esc to exit.");
      return;
    }
    active = true;
    installUi();
    window.addEventListener("mousemove", onMouseMove, true);
    window.addEventListener("click", onClick, true);
    window.addEventListener("keydown", onKeyDown, true);
  }

  function stop() {
    if (!active) {
      return;
    }
    active = false;
    window.removeEventListener("mousemove", onMouseMove, true);
    window.removeEventListener("click", onClick, true);
    window.removeEventListener("keydown", onKeyDown, true);
    removeUi();
  }

  window.__codexElementCapture = {
    start: start,
    stop: stop,
    buildPayload: buildPayload
  };

  start();
})();
