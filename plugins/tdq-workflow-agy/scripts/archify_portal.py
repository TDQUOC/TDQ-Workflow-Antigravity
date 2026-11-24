#!/usr/bin/env python3
"""TDQ Archify Lazy Drill-Down Portal & Standalone HTML Renderer.

Provides:
- build_portal_shell: shared HTML shell (< 300 KB in lazy mode) with external
  [data-node-id] delegation, natural-language drawer, mini-flowchart, breadcrumb,
  cycle anchor guard, HTTP fetch lazy loading, and file:// registry-bundle.js fallback.
- build_registry_bundle_js: safe JS bundle setting window.__TDQ_ARCHIFY_REGISTRY__.
- render_drilldown_standalone: self-contained <= 4 level HTML artifact for Spec/Report.

Strictly stdlib-only (+ sibling archify_registry). Env: TDQ_LOG=0 disables stderr logs.
"""
from __future__ import annotations

import datetime
import html
import json
import os
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import archify_registry

PORTAL_MAX_LAZY_BYTES = 295_000
STANDALONE_MAX_DEPTH = 4
_VALID_MODES = frozenset({"lazy", "embedded"})

_UI_STRINGS: dict[str, dict[str, str]] = {
    "vi": {
        "brand": "Archify Drill-Down Portal",
        "search_placeholder": "Tìm bước, node ID, symbol…",  # i18n-allow
        "theme_toggle": "Sáng / Tối",  # i18n-allow
        "flows_label": "Luồng gốc",  # i18n-allow
        "home": "Tổng quan",  # i18n-allow
        "level": "Tầng",  # i18n-allow
        "fit": "Vừa khung",  # i18n-allow
        "empty_hint": "Chọn một khối trên sơ đồ để xem giải thích tự nhiên và đi sâu.",  # i18n-allow
        "summary": "Tóm tắt",  # i18n-allow
        "what_goes_where": "Dữ liệu đi đâu",  # i18n-allow
        "why_it_exists": "Vì sao tồn tại",  # i18n-allow
        "edge_cases": "Trường hợp biên",  # i18n-allow
        "io_title": "Hợp đồng Vào / Ra",  # i18n-allow
        "inputs": "Đầu vào",  # i18n-allow
        "outputs": "Đầu ra",  # i18n-allow
        "side_effects": "Tác động phụ",  # i18n-allow
        "mini_flow": "Sơ đồ bước con",  # i18n-allow
        "sources": "Bằng chứng mã nguồn",  # i18n-allow
        "used_in_prefix": "Dùng ở",  # i18n-allow
        "used_in_suffix": "luồng",  # i18n-allow
        "cycle_prefix": "↺ Quay về",  # i18n-allow
        "cycle_desc": "Phát hiện chu trình quay lại nút đã mở; không sinh thêm tầng lặp.",  # i18n-allow
        "cycle_jump": "Nhảy về tầng này",  # i18n-allow
        "ev_planned": "Dự kiến (planned)",  # i18n-allow
        "ev_working": "Mã hiện hành (working-tree)",  # i18n-allow
        "ev_committed": "Đã chốt (committed)",  # i18n-allow
        "no_results": "Không tìm thấy nút phù hợp",  # i18n-allow
        "no_subflow": "Nút lá — không có tầng con sâu hơn.",  # i18n-allow
    },
    "en": {
        "brand": "Archify Drill-Down Portal",
        "search_placeholder": "Search steps, node ID, symbol…",
        "theme_toggle": "Light / Dark",
        "flows_label": "Root Flows",
        "home": "Overview",
        "level": "Level",
        "fit": "Fit",
        "empty_hint": "Click any node on the diagram to inspect its plain explanation or drill down.",
        "summary": "Summary",
        "what_goes_where": "What Goes Where",
        "why_it_exists": "Why It Exists",
        "edge_cases": "Edge Cases",
        "io_title": "I/O Contract",
        "inputs": "Inputs",
        "outputs": "Outputs",
        "side_effects": "Side Effects",
        "mini_flow": "Sub-Flow Steps",
        "sources": "Source Evidence",
        "used_in_prefix": "Used in",
        "used_in_suffix": "flows",
        "cycle_prefix": "↺ Return to",
        "cycle_desc": "Cycle detected toward an active breadcrumb node; keeping view loop-free.",
        "cycle_jump": "Jump to Level",
        "ev_planned": "Planned",
        "ev_working": "Working-tree",
        "ev_committed": "Committed",
        "no_results": "No matching nodes",
        "no_subflow": "Leaf node — no deeper sub-flow.",
    },
}

_PORTAL_CSS = """
:root,[data-theme="dark"]{
  --bg:#060c18;--panel:#0f172a;--panel-alt:#162035;--panel-border:#24324b;
  --text:#f1f5f9;--text-muted:#94a3b8;--text-dim:#64748b;--text-faint:#7d8da1;
  --grid:#172338;--lane-fill:rgba(15,23,42,.32);--lane-stroke:#334155;--mask:#0f172a;
  --frontend-fill:rgba(8,51,68,.45);--frontend-stroke:#22d3ee;
  --backend-fill:rgba(6,78,59,.45);--backend-stroke:#34d399;
  --database-fill:rgba(76,29,149,.45);--database-stroke:#a78bfa;
  --cloud-fill:rgba(120,53,15,.35);--cloud-stroke:#fbbf24;
  --security-fill:rgba(136,19,55,.45);--security-stroke:#fb7185;
  --messagebus-fill:rgba(251,146,60,.3);--messagebus-stroke:#fb923c;
  --external-fill:rgba(30,41,59,.55);--external-stroke:#94a3b8;
  --arrow:#94a3b8;--arrow-emphasis:#34d399;--accent:#38bdf8;--accent-soft:rgba(56,189,248,.14);
}
[data-theme="light"]{
  --bg:#f4f6f9;--panel:#ffffff;--panel-alt:#f8fafc;--panel-border:#dbe2ea;
  --text:#0f172a;--text-muted:#475569;--text-dim:#94a3b8;--text-faint:#64748b;
  --grid:#e6ebf2;--lane-fill:rgba(241,245,249,.7);--lane-stroke:#cbd5e1;--mask:#ffffff;
  --frontend-fill:rgba(34,211,238,.15);--frontend-stroke:#0891b2;
  --backend-fill:rgba(52,211,153,.18);--backend-stroke:#059669;
  --database-fill:rgba(167,139,250,.2);--database-stroke:#7c3aed;
  --cloud-fill:rgba(251,191,36,.18);--cloud-stroke:#d97706;
  --security-fill:rgba(251,113,133,.15);--security-stroke:#e11d48;
  --messagebus-fill:rgba(251,146,60,.15);--messagebus-stroke:#ea580c;
  --external-fill:rgba(148,163,184,.18);--external-stroke:#64748b;
  --arrow:#64748b;--arrow-emphasis:#059669;--accent:#2563eb;--accent-soft:#eff6ff;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
button,input{font:inherit;color:inherit}
[hidden]{display:none!important}
.portal-header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;padding:12px 20px;background:var(--panel);border-bottom:1px solid var(--panel-border)}
.portal-title-wrap{display:flex;align-items:center;gap:10px;min-width:0}
.portal-dot{width:10px;height:10px;border-radius:50%;background:var(--accent);flex:none}
.portal-title{margin:0;font-size:1.1rem;font-weight:700;letter-spacing:-.01em}
.portal-controls{display:flex;align-items:center;gap:8px;position:relative}
.portal-search{width:240px;max-width:52vw;padding:6px 10px;border:1px solid var(--panel-border);border-radius:8px;background:var(--panel-alt)}
.portal-btn{padding:6px 10px;border:1px solid var(--panel-border);border-radius:8px;background:var(--panel-alt);cursor:pointer;font-size:12.5px}
.portal-btn:hover{border-color:var(--accent)}
.portal-btn.active{background:var(--accent-soft);border-color:var(--accent);color:var(--accent);font-weight:600}
.portal-search-menu{position:absolute;top:calc(100% + 6px);left:0;width:310px;max-height:280px;overflow:auto;background:var(--panel);border:1px solid var(--panel-border);border-radius:10px;padding:4px;z-index:30;box-shadow:0 10px 28px rgba(0,0,0,.28)}
.portal-search-item{display:flex;justify-content:space-between;gap:8px;width:100%;text-align:left;padding:7px 10px;border:0;border-radius:6px;background:none;cursor:pointer}
.portal-search-item:hover{background:var(--panel-alt)}
.portal-nav{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px;padding:10px 20px;background:var(--panel-alt);border-bottom:1px solid var(--panel-border)}
.portal-flows,.portal-crumbs{display:flex;flex-wrap:wrap;align-items:center;gap:6px}
.portal-crumb-sep{color:var(--text-dim);font-size:12px}
.portal-main{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(320px,1fr);gap:16px;padding:16px 20px;max-width:1540px;margin:0 auto;align-items:start}
@media(max-width:960px){.portal-main{grid-template-columns:1fr}}
.portal-card{background:var(--panel);border:1px solid var(--panel-border);border-radius:12px;overflow:hidden}
.stage-bar{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 14px;border-bottom:1px solid var(--panel-border);background:var(--panel-alt)}
.stage-viewport{padding:16px;min-height:320px;overflow:auto;display:flex;align-items:center;justify-content:center}
.portal-svg-stage{width:100%;transform-origin:top left;transition:transform .14s ease}
.portal-svg-stage>svg{width:100%;height:auto;max-width:100%;display:block;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.drawer-body{padding:16px;display:flex;flex-direction:column;gap:14px}
.drawer-title{margin:0;font-size:1.15rem;font-weight:700}
.badge-row{display:flex;flex-wrap:wrap;gap:6px}
.badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:600;border:1px solid var(--panel-border);background:var(--panel-alt)}
.badge-planned{border-color:var(--cloud-stroke);color:var(--cloud-stroke);background:var(--cloud-fill)}
.badge-working{border-color:var(--frontend-stroke);color:var(--frontend-stroke);background:var(--frontend-fill)}
.badge-committed{border-color:var(--backend-stroke);color:var(--backend-stroke);background:var(--backend-fill)}
.badge-reuse{border-color:var(--database-stroke);color:var(--database-stroke);background:var(--database-fill)}
.cycle-card{padding:12px;border-radius:10px;border:1px solid var(--cloud-stroke);background:var(--cloud-fill);display:flex;flex-direction:column;gap:8px}
.cycle-card strong{color:var(--cloud-stroke)}
.drawer-sec{border-top:1px solid var(--panel-border);padding-top:10px}
.drawer-sec h3{margin:0 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted)}
.drawer-kv{margin:4px 0;font-size:13.5px}
.drawer-kv b{color:var(--text)}
.drawer-list{margin:4px 0 0;padding-left:18px;font-size:13px;color:var(--text-muted)}
.mini-flow-box{border:1px solid var(--panel-border);border-radius:8px;padding:8px;background:var(--panel-alt);overflow-x:auto}
.mini-flow-box svg{width:100%;height:auto;display:block}
.source-chip{display:inline-block;padding:2px 8px;border-radius:6px;background:var(--panel-alt);border:1px solid var(--panel-border);font:12px/1.5 ui-monospace,monospace;margin:2px 4px 2px 0}
.c-grid{stroke:var(--grid);fill:none}.c-mask{fill:var(--mask);stroke:none}.c-lane{fill:var(--lane-fill);stroke:var(--lane-stroke)}
.c-lane-rule{stroke:var(--lane-stroke);fill:none}.c-lane-wash{fill:var(--lane-fill);stroke:none}
.c-security-group{fill:none;stroke:var(--security-stroke);stroke-dasharray:4 3}
.c-region{fill:none;stroke:var(--cloud-stroke)}
.c-frontend{fill:var(--frontend-fill);stroke:var(--frontend-stroke)}.c-backend{fill:var(--backend-fill);stroke:var(--backend-stroke)}
.c-database{fill:var(--database-fill);stroke:var(--database-stroke)}.c-cloud{fill:var(--cloud-fill);stroke:var(--cloud-stroke)}
.c-security{fill:var(--security-fill);stroke:var(--security-stroke)}.c-messagebus{fill:var(--messagebus-fill);stroke:var(--messagebus-stroke)}
.c-external{fill:var(--external-fill);stroke:var(--external-stroke)}
.t-primary{fill:var(--text)}.t-muted{fill:var(--text-muted)}.t-dim{fill:var(--text-dim)}
.t-frontend{fill:var(--frontend-stroke)}.t-backend{fill:var(--backend-stroke)}.t-database{fill:var(--database-stroke)}
.t-cloud{fill:var(--cloud-stroke)}.t-security{fill:var(--security-stroke)}.t-messagebus{fill:var(--messagebus-stroke)}.t-external{fill:var(--external-stroke)}
.t-edge-default{fill:var(--arrow)}.t-edge-emphasis{fill:var(--arrow-emphasis)}.t-edge-security{fill:var(--security-stroke)}.t-edge-dashed{fill:var(--database-stroke)}
.a-default{stroke:var(--arrow);fill:none}.a-emphasis{stroke:var(--arrow-emphasis);fill:none}
.a-security{stroke:var(--security-stroke);fill:none;stroke-dasharray:5,5}.a-dashed{stroke:var(--database-stroke);fill:none;stroke-dasharray:4,4}
.m-default{fill:var(--arrow)}.m-emphasis{fill:var(--arrow-emphasis)}.m-security{fill:var(--security-stroke)}.m-dashed{fill:var(--database-stroke)}
svg .semantic-sigil{fill:none;stroke:currentColor;stroke-width:1.35;stroke-linecap:round;stroke-linejoin:round;pointer-events:none}
svg .semantic-sigil .sigil-fill{fill:currentColor;stroke:none}
svg .s-frontend{color:var(--frontend-stroke)}svg .s-backend{color:var(--backend-stroke)}svg .s-database{color:var(--database-stroke)}
svg .s-cloud{color:var(--cloud-stroke)}svg .s-security{color:var(--security-stroke)}svg .s-messagebus{color:var(--messagebus-stroke)}svg .s-external{color:var(--external-stroke)}
svg [data-node-id],svg [data-cycle-back]{cursor:pointer}
svg [data-node-id]:hover{filter:drop-shadow(0 0 6px var(--accent))}
svg [data-node-id].portal-selected>rect:not(.c-mask){stroke-width:2.5px;filter:drop-shadow(0 0 8px var(--accent))}
"""

_PORTAL_JS = r"""
(function () {
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  }
  function svgEl(tag, attrs) {
    var n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, String(attrs[k])); });
    return n;
  }
  var bootNode = document.getElementById("tdq-portal-bootstrap");
  var boot = bootNode ? JSON.parse(bootNode.textContent || "{}") : {};
  var uiNode = document.getElementById("tdq-portal-ui");
  var UI = uiNode ? JSON.parse(uiNode.textContent || "{}") : {};
  var bundle = window.__TDQ_ARCHIFY_REGISTRY__ || null;
  var index = (boot.index && boot.index.nodes ? boot.index : null) || (bundle && bundle.index) || { root_flows: [], nodes: [], cycles_detected: [] };
  var state = {
    index: index,
    indexMap: {},
    nodeCache: Object.assign({}, (bundle && bundle.nodes) || {}, boot.nodes || {}),
    sliceCache: Object.assign({}, boot.slices || {}),
    breadcrumb: [],
    activeId: null,
    zoom: 1,
  };
  (index.nodes || []).forEach(function (entry) { state.indexMap[entry.node_id] = entry; });
  var isFileProto = typeof window !== "undefined" && window.location && window.location.protocol === "file:";
  var stage = document.getElementById("portal-svg-stage");
  var miniBox = document.getElementById("drawer-mini-flow");

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("archify-portal-theme", theme); } catch (_) {}
  }
  (function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem("archify-portal-theme"); } catch (_) {}
    if (saved !== "light" && saved !== "dark") {
      saved = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }
    setTheme(saved);
  })();
  document.getElementById("portal-theme-btn").addEventListener("click", function () {
    var curr = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
    setTheme(curr === "light" ? "dark" : "light");
  });

  function applyZoom() {
    stage.style.transform = "scale(" + state.zoom.toFixed(2) + ")";
    document.getElementById("portal-zoom-pct").textContent = Math.round(state.zoom * 100) + "%";
  }
  document.getElementById("portal-zoom-out").addEventListener("click", function () { state.zoom = Math.max(0.5, state.zoom - 0.15); applyZoom(); });
  document.getElementById("portal-zoom-in").addEventListener("click", function () { state.zoom = Math.min(2.2, state.zoom + 0.15); applyZoom(); });
  document.getElementById("portal-zoom-reset").addEventListener("click", function () { state.zoom = 1; applyZoom(); });

  function bundleRef() { return window.__TDQ_ARCHIFY_REGISTRY__ || bundle; }

  async function loadNode(nodeId) {
    if (state.nodeCache[nodeId]) return state.nodeCache[nodeId];
    var b = bundleRef();
    if (isFileProto && b && b.nodes && b.nodes[nodeId]) {
      state.nodeCache[nodeId] = b.nodes[nodeId];
      return state.nodeCache[nodeId];
    }
    if (!isFileProto && typeof fetch === "function") {
      try {
        var r = await fetch("nodes/" + encodeURIComponent(nodeId) + ".json");
        if (r.ok) {
          var parsed = await r.json();
          state.nodeCache[nodeId] = parsed;
          return parsed;
        }
      } catch (_) {}
    }
    if (b && b.nodes && b.nodes[nodeId]) {
      state.nodeCache[nodeId] = b.nodes[nodeId];
      return state.nodeCache[nodeId];
    }
    return state.indexMap[nodeId] || null;
  }

  async function loadSlice(sliceId) {
    if (!sliceId) return null;
    if (state.sliceCache[sliceId]) return state.sliceCache[sliceId];
    var b = bundleRef();
    if (isFileProto && b && b.slices && b.slices[sliceId]) {
      state.sliceCache[sliceId] = b.slices[sliceId];
      return state.sliceCache[sliceId];
    }
    if (!isFileProto && typeof fetch === "function") {
      try {
        var r = await fetch("slices/" + encodeURIComponent(sliceId) + ".svg");
        if (r.ok) {
          var txt = await r.text();
          state.sliceCache[sliceId] = txt;
          return txt;
        }
      } catch (_) {}
    }
    if (b && b.slices && b.slices[sliceId]) {
      state.sliceCache[sliceId] = b.slices[sliceId];
      return state.sliceCache[sliceId];
    }
    return null;
  }

  function sanitizeSvg(markup) {
    var tpl = document.createElement("template");
    tpl.innerHTML = String(markup || "");
    var svg = tpl.content.querySelector("svg");
    if (!svg) return null;
    svg.querySelectorAll("script,foreignObject").forEach(function (n) { n.remove(); });
    svg.querySelectorAll("*").forEach(function (n) {
      Array.prototype.slice.call(n.attributes).forEach(function (a) {
        var nm = a.name.toLowerCase();
        if (nm.indexOf("on") === 0 || (a.value || "").trim().toLowerCase().indexOf("javascript:") === 0) {
          n.removeAttribute(a.name);
        }
      });
    });
    return svg;
  }

  function buildSubflowSvg(node, highlightId) {
    var sf = node && node.sub_flow;
    if (!sf || !Array.isArray(sf.steps) || !sf.steps.length) return null;
    var laneIdx = { main: 0, branch: 1, error: 2 };
    var w = Math.max(420, (sf.max_cols || sf.steps.length) * 165 + 40);
    var h = 220;
    var svg = svgEl("svg", { viewBox: "0 0 " + w + " " + h, role: "img" });
    var pos = {};
    sf.steps.forEach(function (st, idx) {
      var col = typeof st.col === "number" ? st.col : idx;
      var row = laneIdx[st.lane || "main"] || 0;
      pos[st.step_id] = { x: 20 + col * 160, y: 20 + row * 66 };
    });
    (sf.edges || []).forEach(function (ed) {
      var p1 = pos[ed.from];
      var p2 = pos[ed.to];
      if (!p1 || !p2) return;
      svg.appendChild(svgEl("line", {
        x1: p1.x + 136, y1: p1.y + 24, x2: p2.x, y2: p2.y + 24,
        class: "a-emphasis", "stroke-width": 1.6,
      }));
    });
    sf.steps.forEach(function (st) {
      var p = pos[st.step_id];
      var attrs = { tabindex: 0, role: "button" };
      if (st.cycle_back_to) {
        attrs["data-cycle-back"] = st.cycle_back_to;
      } else if (st.target_node_id) {
        attrs["data-node-id"] = st.target_node_id;
      }
      var cls = st.lane === "error" ? "c-security" : (st.lane === "branch" ? "c-cloud" : "c-backend");
      var g = svgEl("g", attrs);
      if (highlightId && st.target_node_id === highlightId) g.classList.add("portal-selected");
      g.appendChild(svgEl("rect", { x: p.x, y: p.y, width: 136, height: 48, rx: 8, class: cls, "stroke-width": 1.5 }));
      var lbl = (st.cycle_back_to ? "↺ " : "") + (st.label || st.step_id);
      var t = svgEl("text", { x: p.x + 68, y: p.y + 28, class: "t-primary", "font-size": 11, "text-anchor": "middle" });
      t.textContent = lbl.length > 18 ? lbl.slice(0, 17) + "…" : lbl;
      g.appendChild(t);
      svg.appendChild(g);
    });
    return svg;
  }

  function highlightStageNode(nodeId) {
    stage.querySelectorAll("[data-node-id]").forEach(function (elNode) {
      var match = elNode.getAttribute("data-node-id") === nodeId;
      elNode.classList.toggle("portal-selected", match);
    });
  }

  function showCycleAnchor(targetId, label, targetIdx) {
    var box = document.getElementById("portal-cycle-banner");
    box.replaceChildren();
    box.hidden = false;
    var lvl = targetIdx >= 0 ? " (" + UI.level + " " + (targetIdx + 1) + ")" : "";
    var titleEl = el("strong", "", UI.cycle_prefix + ' "' + (label || targetId) + '"' + lvl);
    var descEl = el("div", "", UI.cycle_desc);
    var btn = el("button", "portal-btn active", UI.cycle_jump);
    btn.type = "button";
    btn.addEventListener("click", function () {
      box.hidden = true;
      if (targetIdx >= 0) {
        jumpToBreadcrumb(targetIdx);
      } else {
        selectNode(targetId, { replaceAll: true });
      }
    });
    box.appendChild(titleEl);
    box.appendChild(descEl);
    box.appendChild(btn);
  }

  function hideCycleAnchor() {
    var box = document.getElementById("portal-cycle-banner");
    box.hidden = true;
    box.replaceChildren();
  }

  function renderFlowsAndCrumbs() {
    var flowsBox = document.getElementById("portal-flows");
    flowsBox.replaceChildren();
    var rootIds = (state.index.root_flows || []).length ? state.index.root_flows : (state.index.nodes[0] ? [state.index.nodes[0].node_id] : []);
    rootIds.forEach(function (rid) {
      var entry = state.indexMap[rid];
      var b = el("button", "portal-btn", entry ? entry.title : rid);
      b.type = "button";
      if (state.breadcrumb[0] && state.breadcrumb[0].nodeId === rid) b.classList.add("active");
      b.addEventListener("click", function () { selectNode(rid, { replaceAll: true }); });
      flowsBox.appendChild(b);
    });
    var crumbsBox = document.getElementById("portal-breadcrumb");
    crumbsBox.replaceChildren();
    var homeBtn = el("button", "portal-btn", UI.home);
    homeBtn.type = "button";
    homeBtn.addEventListener("click", function () {
      if (state.breadcrumb.length) jumpToBreadcrumb(0);
    });
    crumbsBox.appendChild(homeBtn);
    state.breadcrumb.forEach(function (crumb, idx) {
      crumbsBox.appendChild(el("span", "portal-crumb-sep", "›"));
      var cBtn = el("button", "portal-btn", UI.level + " " + (idx + 1) + ": " + crumb.title);
      cBtn.type = "button";
      if (idx === state.breadcrumb.length - 1) cBtn.classList.add("active");
      cBtn.addEventListener("click", function () { jumpToBreadcrumb(idx); });
      crumbsBox.appendChild(cBtn);
    });
  }

  function appendList(parent, label, items) {
    if (!items || !items.length) return;
    var p = el("div", "drawer-kv");
    p.appendChild(el("b", "", label + ": "));
    parent.appendChild(p);
    var ul = el("ul", "drawer-list");
    items.forEach(function (it) { ul.appendChild(el("li", "", it)); });
    parent.appendChild(ul);
  }

  function renderDrawer(node, domFallback) {
    document.getElementById("portal-empty").hidden = true;
    var titleEl = document.getElementById("drawer-title");
    var badgesEl = document.getElementById("drawer-badges");
    var expEl = document.getElementById("drawer-explanation");
    var ioEl = document.getElementById("drawer-io");
    var srcEl = document.getElementById("drawer-sources");
    badgesEl.replaceChildren();
    expEl.replaceChildren();
    ioEl.replaceChildren();
    srcEl.replaceChildren();
    miniBox.replaceChildren();

    if (!node) {
      titleEl.textContent = (domFallback && domFallback.label) || state.activeId || "";
      if (domFallback && domFallback.sublabel) expEl.appendChild(el("p", "drawer-kv", domFallback.sublabel));
      return;
    }
    titleEl.textContent = node.title || node.node_id;
    var ev = node.evidence_kind || "working-tree";
    var evCls = ev === "planned" ? "badge-planned" : (ev === "committed" ? "badge-committed" : "badge-working");
    var evTxt = ev === "planned" ? UI.ev_planned : (ev === "committed" ? UI.ev_committed : UI.ev_working);
    badgesEl.appendChild(el("span", "badge " + evCls, evTxt));
    if (node.node_kind) badgesEl.appendChild(el("span", "badge", node.node_kind));
    var reused = Array.isArray(node.reused_by) ? node.reused_by : [];
    if (reused.length) {
      badgesEl.appendChild(el("span", "badge badge-reuse", UI.used_in_prefix + " " + reused.length + " " + UI.used_in_suffix + " (" + reused.join(", ") + ")"));
    }
    var ne = node.natural_explanation || {};
    [["summary", UI.summary], ["what_goes_where", UI.what_goes_where], ["why_it_exists", UI.why_it_exists]].forEach(function (pair) {
      if (!ne[pair[0]]) return;
      var line = el("p", "drawer-kv");
      line.appendChild(el("b", "", pair[1] + ": "));
      line.appendChild(document.createTextNode(String(ne[pair[0]])));
      expEl.appendChild(line);
    });
    appendList(expEl, UI.edge_cases, ne.edge_cases);
    var io = node.io_contract || {};
    appendList(ioEl, UI.inputs, io.inputs);
    appendList(ioEl, UI.outputs, io.outputs);
    appendList(ioEl, UI.side_effects, io.side_effects);
    var sfSvg = buildSubflowSvg(node, null);
    if (sfSvg) {
      miniBox.appendChild(sfSvg);
    } else {
      miniBox.appendChild(el("span", "", UI.no_subflow));
    }
    (node.sources || []).forEach(function (src) {
      var rng = src.end_line && src.end_line !== src.line ? src.line + "-" + src.end_line : String(src.line);
      srcEl.appendChild(el("span", "source-chip", src.path + ":" + rng));
    });
    if (node.fingerprint && node.fingerprint.symbol_ref) {
      srcEl.appendChild(el("span", "source-chip", node.fingerprint.symbol_ref));
    } else if (node.symbol_ref) {
      srcEl.appendChild(el("span", "source-chip", node.symbol_ref));
    }
  }

  async function mountActiveStage(highlightId) {
    var ownerCrumb = null;
    for (var i = state.breadcrumb.length - 1; i >= 0; i -= 1) {
      if (state.breadcrumb[i].hasChild) { ownerCrumb = state.breadcrumb[i]; break; }
    }
    if (!ownerCrumb) ownerCrumb = state.breadcrumb[0];
    if (!ownerCrumb) return;
    var ownerNode = await loadNode(ownerCrumb.nodeId);
    var sliceId = ownerCrumb.sliceId || (ownerNode && ownerNode.sub_flow && ownerNode.sub_flow.slice_id) || (ownerNode && ownerNode.sub_flow_slice_id);
    var svgText = sliceId ? await loadSlice(sliceId) : null;
    var svgElNode = svgText ? sanitizeSvg(svgText) : buildSubflowSvg(ownerNode, highlightId);
    stage.replaceChildren();
    if (svgElNode) stage.appendChild(svgElNode);
    highlightStageNode(highlightId);
  }

  async function jumpToBreadcrumb(idx) {
    if (idx < 0 || idx >= state.breadcrumb.length) return;
    hideCycleAnchor();
    state.breadcrumb = state.breadcrumb.slice(0, idx + 1);
    var target = state.breadcrumb[idx];
    state.activeId = target.nodeId;
    var node = await loadNode(target.nodeId);
    renderFlowsAndCrumbs();
    renderDrawer(node, null);
    await mountActiveStage(target.nodeId);
  }

  async function selectNode(nodeId, opts) {
    opts = opts || {};
    if (opts.cycleBackTo) {
      var backIdx = state.breadcrumb.findIndex(function (b) { return b.nodeId === opts.cycleBackTo; });
      var backTitle = (state.indexMap[opts.cycleBackTo] && state.indexMap[opts.cycleBackTo].title) || opts.cycleBackTo;
      showCycleAnchor(opts.cycleBackTo, backTitle, backIdx);
      return;
    }
    if (!opts.replaceAll) {
      var existingIdx = state.breadcrumb.findIndex(function (b) { return b.nodeId === nodeId; });
      if (existingIdx >= 0 && (existingIdx < state.breadcrumb.length - 1 || opts.fromSubFlowStep)) {
        showCycleAnchor(nodeId, state.breadcrumb[existingIdx].title, existingIdx);
        return;
      }
    }
    hideCycleAnchor();
    var node = await loadNode(nodeId);
    if (!node) {
      state.activeId = nodeId;
      highlightStageNode(nodeId);
      renderDrawer(null, opts.domFallback || { label: nodeId });
      return;
    }
    var sliceId = (node.sub_flow && node.sub_flow.slice_id) || node.sub_flow_slice_id || null;
    var hasChild = Boolean(sliceId || (node.sub_flow && node.sub_flow.steps && node.sub_flow.steps.length));
    var crumb = { nodeId: nodeId, title: node.title || nodeId, sliceId: sliceId, hasChild: hasChild };
    if (opts.replaceAll || !state.breadcrumb.length) {
      state.breadcrumb = [crumb];
    } else {
      var top = state.breadcrumb[state.breadcrumb.length - 1];
      if (top.nodeId === nodeId) {
        state.breadcrumb[state.breadcrumb.length - 1] = crumb;
      } else {
        if (!top.hasChild) state.breadcrumb.pop();
        state.breadcrumb.push(crumb);
      }
    }
    state.activeId = nodeId;
    renderFlowsAndCrumbs();
    renderDrawer(node, null);
    await mountActiveStage(nodeId);
  }

  function handleContainerEvent(container, isSubFlow) {
    container.addEventListener("click", function (ev) {
      var cyc = ev.target && ev.target.closest ? ev.target.closest("[data-cycle-back]") : null;
      if (cyc && container.contains(cyc)) {
        selectNode(cyc.getAttribute("data-cycle-back"), { cycleBackTo: cyc.getAttribute("data-cycle-back") });
        return;
      }
      var targetEl = ev.target && ev.target.closest ? ev.target.closest("[data-node-id]") : null;
      if (!targetEl || !container.contains(targetEl)) return;
      var nid = targetEl.getAttribute("data-node-id");
      if (nid) {
        selectNode(nid, {
          fromSubFlowStep: isSubFlow,
          domFallback: { label: targetEl.getAttribute("data-node-label"), sublabel: targetEl.getAttribute("data-node-sublabel") },
        });
      }
    });
    container.addEventListener("keydown", function (ev) {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      var targetEl = ev.target && ev.target.closest ? ev.target.closest("[data-node-id]") : null;
      if (!targetEl || !container.contains(targetEl)) return;
      ev.preventDefault();
      targetEl.click();
    });
  }
  handleContainerEvent(stage, false);
  handleContainerEvent(miniBox, true);

  (function initSearch() {
    var input = document.getElementById("portal-search");
    var menu = document.getElementById("portal-search-results");
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      menu.replaceChildren();
      if (!q) { menu.hidden = true; return; }
      var hits = (state.index.nodes || []).filter(function (n) {
        return (n.node_id + " " + (n.title || "") + " " + (n.symbol_ref || "")).toLowerCase().indexOf(q) >= 0;
      }).slice(0, 12);
      if (!hits.length) {
        menu.appendChild(el("div", "portal-search-item", UI.no_results));
      } else {
        hits.forEach(function (h) {
          var b = el("button", "portal-search-item");
          b.type = "button";
          b.appendChild(el("span", "", h.title || h.node_id));
          b.appendChild(el("small", "", "L" + (h.depth || 1)));
          b.addEventListener("click", function () {
            menu.hidden = true;
            input.value = "";
            selectNode(h.node_id, { replaceAll: h.depth === 1 });
          });
          menu.appendChild(b);
        });
      }
      menu.hidden = false;
    });
    document.addEventListener("click", function (ev) {
      if (!menu.contains(ev.target) && ev.target !== input) menu.hidden = true;
    });
  })();

  var initialRoot = (state.index.root_flows || [])[0] || (state.index.nodes[0] && state.index.nodes[0].node_id);
  if (initialRoot) selectNode(initialRoot, { replaceAll: true });
})();
"""


def _log_enabled() -> bool:
    """Return True unless stderr logging is disabled via TDQ_LOG=0."""
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message: str) -> None:
    """Emit one ISO-timestamped log line to stderr."""
    if _log_enabled():
        stamp = datetime.datetime.now().replace(microsecond=0).isoformat()
        print(f"[{stamp}] archify_portal: {message}", file=sys.stderr)


def _lang_key(doc_lang: str) -> str:
    """Normalize document language code to supported UI dictionary key."""
    return "vi" if str(doc_lang or "vi").strip().lower().startswith("vi") else "en"


def _serialize_safe_json(payload: Any) -> str:
    """Serialize JSON safely so embedded script payloads cannot break out of script tags."""
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    for ch, esc in (
        ("<", "\\u003c"),
        (">", "\\u003e"),
        ("&", "\\u0026"),
        ("\u2028", "\\u2028"),
        ("\u2029", "\\u2029"),
    ):
        raw = raw.replace(ch, esc)
    return raw


def _compact_index_entry(entry: dict[str, Any] | None, node: dict[str, Any] | None) -> dict[str, Any]:
    """Build one compact index node summary preserving navigation and badge fields."""
    src = entry if isinstance(entry, dict) else {}
    nd = node if isinstance(node, dict) else {}
    fp = nd.get("fingerprint") if isinstance(nd.get("fingerprint"), dict) else {}
    sf = nd.get("sub_flow") if isinstance(nd.get("sub_flow"), dict) else {}
    return {
        "node_id": src.get("node_id") or nd.get("node_id", ""),
        "title": src.get("title") or nd.get("title") or src.get("node_id") or nd.get("node_id", ""),
        "depth": src.get("depth") or nd.get("depth", 1),
        "node_kind": src.get("node_kind") or nd.get("node_kind", "decision_branch"),
        "hydration_tier": src.get("hydration_tier") or nd.get("hydration_tier", "eager_l1_l2"),
        "evidence_kind": src.get("evidence_kind") or nd.get("evidence_kind", "working-tree"),
        "symbol_ref": src.get("symbol_ref") or fp.get("symbol_ref", ""),
        "sub_flow_slice_id": src.get("sub_flow_slice_id") or sf.get("slice_id"),
        "reused_by": list(src.get("reused_by") or nd.get("reused_by") or []),
        "cache_status": src.get("cache_status") or fp.get("cache_status", "clean"),
        "span_binding": src.get("span_binding") or fp.get("span_binding"),
    }


def _normalize_registry_index(
    registry_index: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    max_depth: int = 6,
) -> dict[str, Any]:
    """Normalize registry index metadata, root_flows, and cycle records cleanly."""
    idx = dict(registry_index) if isinstance(registry_index, dict) else {}
    by_id: dict[str, dict[str, Any]] = {}
    for entry in idx.get("nodes", []) if isinstance(idx.get("nodes"), list) else []:
        if isinstance(entry, dict) and entry.get("node_id"):
            by_id[str(entry["node_id"])] = entry

    all_ids = sorted(set(by_id) | set(nodes))
    compact_nodes = [_compact_index_entry(by_id.get(nid), nodes.get(nid)) for nid in all_ids]
    root_flows = [str(r) for r in idx.get("root_flows", []) if isinstance(r, str) and r]
    if not root_flows and compact_nodes:
        root_flows = [
            e["node_id"] for e in compact_nodes
            if e.get("depth") == 1 or e.get("node_kind") == "flow_root"
        ] or [compact_nodes[0]["node_id"]]

    cycles = idx.get("cycles_detected")
    if cycles is None and nodes:
        _, cycles = archify_registry._detect_all_cycles(nodes, int(idx.get("max_depth", max_depth)))

    return {
        "schema_version": str(idx.get("schema_version", "1.0")),
        "max_depth": int(idx.get("max_depth", max_depth)),
        "root_flows": root_flows,
        "node_count": len(compact_nodes),
        "cycles_detected": list(cycles or []),
        "nodes": compact_nodes,
    }


def _is_eager_node(node_summary: dict[str, Any], root_flows: set[str]) -> bool:
    """Return True when node belongs to overview/L1-L2 eager hydration tier."""
    nid = str(node_summary.get("node_id", ""))
    tier = node_summary.get("hydration_tier")
    depth = node_summary.get("depth", 1)
    return nid in root_flows or tier == "eager_l1_l2" or (isinstance(depth, int) and depth <= 2)


def _select_eager_slices(
    index: dict[str, Any],
    slices: dict[str, str],
    budget_bytes: int,
) -> dict[str, str]:
    """Select eager L1/L2 slices strictly within the lazy HTML byte budget."""
    roots = set(index.get("root_flows") or [])
    ordered_slice_ids: list[str] = []
    for entry in sorted(
        index.get("nodes", []),
        key=lambda e: (0 if e.get("node_id") in roots else 1, int(e.get("depth") or 1)),
    ):
        sid = entry.get("sub_flow_slice_id")
        if sid and sid in slices and _is_eager_node(entry, roots) and sid not in ordered_slice_ids:
            ordered_slice_ids.append(str(sid))

    if "overview" in slices and "overview" not in ordered_slice_ids:
        ordered_slice_ids.insert(0, "overview")

    selected: dict[str, str] = {}
    used = len(_serialize_safe_json({"index": index, "slices": {}, "nodes": {}}).encode("utf-8"))
    for sid in ordered_slice_ids:
        candidate_json = _serialize_safe_json({sid: slices[sid]})
        cost = len(candidate_json.encode("utf-8")) + 16
        if used + cost <= budget_bytes:
            selected[sid] = slices[sid]
            used += cost
    return selected


def _render_body_html(safe_title: str, ui: dict[str, str]) -> str:
    """Render static portal shell body markup using escaped strings and zero inline handlers."""
    return (
        f'<header class="portal-header">'
        f'<div class="portal-title-wrap"><span class="portal-dot" aria-hidden="true"></span>'
        f'<h1 class="portal-title">{safe_title}</h1></div>'
        f'<div class="portal-controls">'
        f'<input id="portal-search" class="portal-search" type="search" '
        f'placeholder="{html.escape(ui["search_placeholder"], quote=True)}" '
        f'aria-label="{html.escape(ui["search_placeholder"], quote=True)}">'
        f'<div id="portal-search-results" class="portal-search-menu" hidden></div>'
        f'<button id="portal-theme-btn" class="portal-btn" type="button">'
        f'{html.escape(ui["theme_toggle"])}</button>'
        f"</div></header>"
        f'<nav class="portal-nav" aria-label="Navigation">'
        f'<div id="portal-flows" class="portal-flows"></div>'
        f'<div id="portal-breadcrumb" class="portal-crumbs"></div>'
        f"</nav>"
        f'<main class="portal-main">'
        f'<section class="portal-card">'
        f'<div class="stage-bar">'
        f'<span class="badge">{html.escape(ui["brand"])}</span>'
        f'<div class="portal-controls">'
        f'<button id="portal-zoom-out" class="portal-btn" type="button">-</button>'
        f'<button id="portal-zoom-reset" class="portal-btn" type="button">'
        f'{html.escape(ui["fit"])} <span id="portal-zoom-pct">100%</span></button>'
        f'<button id="portal-zoom-in" class="portal-btn" type="button">+</button>'
        f"</div></div>"
        f'<div class="stage-viewport"><div id="portal-svg-stage" class="portal-svg-stage"></div></div>'
        f"</section>"
        f'<aside id="portal-drawer" class="portal-card drawer-body">'
        f'<h2 id="drawer-title" class="drawer-title"></h2>'
        f'<div id="drawer-badges" class="badge-row"></div>'
        f'<div id="portal-cycle-banner" class="cycle-card" hidden></div>'
        f'<p id="portal-empty" class="drawer-kv">{html.escape(ui["empty_hint"])}</p>'
        f'<div id="drawer-explanation" class="drawer-sec"></div>'
        f'<div id="drawer-io" class="drawer-sec"><h3>{html.escape(ui["io_title"])}</h3></div>'
        f'<div class="drawer-sec"><h3>{html.escape(ui["mini_flow"])}</h3>'
        f'<div id="drawer-mini-flow" class="mini-flow-box"></div></div>'
        f'<div class="drawer-sec"><h3>{html.escape(ui["sources"])}</h3>'
        f'<div id="drawer-sources"></div></div>'
        f"</aside></main>"
    )


def _render_portal_document(
    bootstrap_payload: dict[str, Any],
    *,
    mode: str,
    title: str,
    doc_lang: str,
    inline_bundle_payload: dict[str, Any] | None = None,
) -> str:
    """Assemble full HTML5 portal document for lazy or embedded delivery."""
    lang = _lang_key(doc_lang)
    ui = _UI_STRINGS[lang]
    safe_title = html.escape(str(title or "Archify Portal"), quote=True)
    body_html = _render_body_html(safe_title, ui)
    boot_json = _serialize_safe_json(bootstrap_payload)
    ui_json = _serialize_safe_json(ui)

    if mode == "lazy":
        fallback_tag = '<script src="registry-bundle.js"></script>'
    else:
        bundle_json = _serialize_safe_json(inline_bundle_payload or bootstrap_payload)
        fallback_tag = f"<script>window.__TDQ_ARCHIFY_REGISTRY__ = {bundle_json};</script>"

    return (
        f"<!doctype html>\n"
        f'<html lang="{lang}" data-theme="dark">\n'
        f"<head>\n"
        f'<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<link rel="icon" href="data:,">\n'
        f"<title>{safe_title}</title>\n"
        f"<style>{_PORTAL_CSS}</style>\n"
        f"</head>\n"
        f"<body>\n"
        f"{body_html}\n"
        f'<script id="tdq-portal-bootstrap" type="application/json">{boot_json}</script>\n'
        f'<script id="tdq-portal-ui" type="application/json">{ui_json}</script>\n'
        f"{fallback_tag}\n"
        f"<script>{_PORTAL_JS}</script>\n"
        f"</body>\n"
        f"</html>\n"
    )


def build_registry_bundle_js(
    registry_index: dict[str, Any],
    slices: dict[str, str],
    nodes: dict[str, dict[str, Any]],
) -> str:
    """Build registry-bundle.js setting window.__TDQ_ARCHIFY_REGISTRY__ for file:// fallback."""
    if not isinstance(slices, dict) or not isinstance(nodes, dict):
        raise TypeError("slices and nodes must be dictionaries")
    norm_index = _normalize_registry_index(registry_index, nodes)
    payload = {"index": norm_index, "slices": dict(slices), "nodes": dict(nodes)}
    js_text = f"window.__TDQ_ARCHIFY_REGISTRY__ = {_serialize_safe_json(payload)};\n"
    _log(f"built registry-bundle.js: nodes={len(nodes)} slices={len(slices)} bytes={len(js_text.encode('utf-8'))}")
    return js_text


def build_portal_shell(
    registry_index: dict[str, Any],
    slices: dict[str, str],
    nodes: dict[str, dict[str, Any]],
    *,
    mode: str = "lazy",
    title: str = "Archify Portal",
    doc_lang: str = "vi",
) -> str:
    """Generate the shared Lazy or Embedded Drill-Down Portal HTML document."""
    if mode not in _VALID_MODES:
        raise ValueError(f"Unsupported portal mode {mode!r}; expected one of {sorted(_VALID_MODES)}")
    if not isinstance(slices, dict) or not isinstance(nodes, dict):
        raise TypeError("slices and nodes must be dictionaries")

    norm_index = _normalize_registry_index(registry_index, nodes)
    if mode == "embedded":
        full_payload = {"index": norm_index, "slices": dict(slices), "nodes": dict(nodes)}
        out = _render_portal_document(
            full_payload,
            mode="embedded",
            title=title,
            doc_lang=doc_lang,
            inline_bundle_payload=full_payload,
        )
        _log(f"built portal shell: mode=embedded nodes={len(nodes)} bytes={len(out.encode('utf-8'))}")
        return out

    shell_overhead = len(
        _render_portal_document({"index": {}, "slices": {}, "nodes": {}}, mode="lazy", title=title, doc_lang=doc_lang)
        .encode("utf-8")
    )
    budget = max(0, PORTAL_MAX_LAZY_BYTES - shell_overhead - 2048)
    eager_slices = _select_eager_slices(norm_index, slices, budget)
    boot_payload = {"index": norm_index, "slices": eager_slices, "nodes": {}}
    out = _render_portal_document(boot_payload, mode="lazy", title=title, doc_lang=doc_lang)
    if len(out.encode("utf-8")) >= 300_000:
        boot_payload["slices"] = {}
        out = _render_portal_document(boot_payload, mode="lazy", title=title, doc_lang=doc_lang)
    if len(out.encode("utf-8")) >= 300_000:
        raise ValueError("Lazy portal index metadata exceeds 300 KB shell size budget")
    _log(
        f"built portal shell: mode=lazy nodes={len(nodes)} eager_slices={len(boot_payload['slices'])} "
        f"bytes={len(out.encode('utf-8'))}"
    )
    return out


def _extract_candidate_nodes(candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract node mapping from a standalone drilldown candidate dictionary."""
    raw_nodes = candidate.get("nodes")
    if isinstance(raw_nodes, dict):
        return {str(k): v for k, v in raw_nodes.items() if isinstance(v, dict)}
    if isinstance(raw_nodes, list):
        out: dict[str, dict[str, Any]] = {}
        for item in raw_nodes:
            if not isinstance(item, dict) or not item.get("node_id"):
                raise ValueError("Each item in candidate.nodes list must be a dict with node_id")
            nid = str(item["node_id"])
            if nid in out:
                raise ValueError(f"Duplicate node_id {nid!r} in standalone candidate")
            out[nid] = item
        return out
    raise ValueError("Standalone drilldown candidate must provide 'nodes' as a dict or list")


def _build_light_candidate_node(
    node: dict[str, Any],
    nid: str,
    title: str,
    depth: int,
    ev: str,
    sources: list[Any],
) -> dict[str, Any]:
    """Build normalized display structure for a lightweight candidate node."""
    ne = dict(node.get("natural_explanation") or {})
    io_c = dict(node.get("io_contract") or {})
    out = dict(node)
    out.setdefault("node_kind", "flow_root" if depth == 1 else "decision_branch")
    out.setdefault("hydration_tier", "eager_l1_l2" if depth <= 2 else "lazy_l3_plus")
    out["evidence_kind"] = ev
    out["natural_explanation"] = {
        "summary": str(ne.get("summary") or title),
        "what_goes_where": str(ne.get("what_goes_where") or ""),
        "why_it_exists": str(ne.get("why_it_exists") or ""),
        "edge_cases": list(ne.get("edge_cases") or []),
    }
    out["io_contract"] = {
        "inputs": list(io_c.get("inputs") or []),
        "outputs": list(io_c.get("outputs") or []),
        "side_effects": list(io_c.get("side_effects") or []),
    }
    out["sources"] = list(sources)
    out["reused_by"] = list(node.get("reused_by") or [])
    return out


def _normalize_candidate_node(node: dict[str, Any], default_evidence: str) -> dict[str, Any]:
    """Validate and normalize one node for standalone drilldown rendering (depth <= 4)."""
    if "fingerprint" in node:
        validated = archify_registry.validate_logic_node(node)
        if validated["depth"] > STANDALONE_MAX_DEPTH:
            raise ValueError(f"Node '{validated['node_id']}' depth {validated['depth']} exceeds standalone limit 4")
        return dict(validated)

    nid = node.get("node_id")
    if not isinstance(nid, str) or not archify_registry._ID_RE.fullmatch(nid):
        raise ValueError(f"Invalid node_id: {nid!r}")
    title = node.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"Node '{nid}' title must be a non-empty string")
    depth = node.get("depth", 1)
    if not archify_registry._is_int(depth) or depth < 1 or depth > STANDALONE_MAX_DEPTH:
        raise ValueError(f"Node '{nid}' depth must be 1..{STANDALONE_MAX_DEPTH}, got {depth!r}")
    ev = str(node.get("evidence_kind") or default_evidence)
    if ev not in archify_registry._VALID_EVIDENCE:
        raise ValueError(f"Node '{nid}' invalid evidence_kind: {ev!r}")
    if "sub_flow" in node and node["sub_flow"] is not None:
        archify_registry._validate_sub_flow(node["sub_flow"], nid)
    sources = archify_registry._require_list(node.get("sources") or [], f"Node '{nid}' sources")
    for idx, src in enumerate(sources):
        archify_registry._validate_span_dict(src, f"{nid}.sources[{idx}]")
    return _build_light_candidate_node(node, nid, title, depth, ev, sources)


def _resolve_standalone_roots(candidate: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> list[str]:
    """Determine valid root flow IDs for standalone drilldown candidate."""
    raw_roots = candidate.get("root_flows") or (candidate.get("registry_index") or {}).get("root_flows") or []
    roots = [str(r) for r in raw_roots if isinstance(r, str) and r in nodes]
    if roots:
        return roots
    depth1 = [nid for nid, n in sorted(nodes.items()) if n.get("depth") == 1 or n.get("node_kind") == "flow_root"]
    return depth1 or [min(nodes)]


def _check_graph_depth_limit(
    nodes: dict[str, dict[str, Any]],
    root_flows: list[str],
    max_allowed: int = STANDALONE_MAX_DEPTH,
) -> None:
    """Verify no simple acyclic path from any root exceeds max_allowed levels."""
    def _walk(curr_id: str, stack: list[str]) -> None:
        if len(stack) > max_allowed:
            raise ValueError(f"Standalone drilldown depth exceeds maximum of {max_allowed} levels")
        for _, target_id, _ in archify_registry._collect_step_targets(nodes[curr_id]):
            if not target_id or target_id not in nodes or target_id in stack:
                continue
            stack.append(target_id)
            _walk(target_id, stack)
            stack.pop()

    for root_id in root_flows:
        if root_id in nodes:
            _walk(root_id, [root_id])


def _merge_candidate_slices(candidate: dict[str, Any], slices: dict[str, str] | None) -> dict[str, str]:
    """Merge optional candidate.slices and explicit slices dictionary safely."""
    merged: dict[str, str] = {}
    cand_slices = candidate.get("slices")
    if cand_slices is not None:
        if not isinstance(cand_slices, dict):
            raise ValueError("candidate.slices must be a dictionary when provided")
        for k, v in cand_slices.items():
            merged[str(k)] = str(v)
    if slices is not None:
        if not isinstance(slices, dict):
            raise ValueError("slices must be a dictionary or None")
        for k, v in slices.items():
            merged[str(k)] = str(v)
    return merged


def render_drilldown_standalone(
    candidate: dict[str, Any],
    slices: dict[str, str] | None = None,
    *,
    doc_lang: str = "vi",
) -> str:
    """Render a completely self-contained <= 4 level Drill-Down HTML artifact."""
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dictionary")

    raw_max = candidate.get("max_depth")
    if raw_max is not None and (
        not archify_registry._is_int(raw_max) or raw_max < 1 or raw_max > STANDALONE_MAX_DEPTH
    ):
        raise ValueError(f"Standalone drilldown max_depth must be 1..{STANDALONE_MAX_DEPTH}, got {raw_max!r}")

    default_evidence = str(candidate.get("evidence_kind") or "planned")
    if default_evidence not in archify_registry._VALID_EVIDENCE:
        raise ValueError(f"Invalid candidate evidence_kind: {default_evidence!r}")

    raw_nodes = _extract_candidate_nodes(candidate)
    if not raw_nodes:
        raise ValueError("Standalone drilldown candidate must contain at least one node")
    norm_nodes = {nid: _normalize_candidate_node(node, default_evidence) for nid, node in raw_nodes.items()}
    root_flows = _resolve_standalone_roots(candidate, norm_nodes)
    _check_graph_depth_limit(norm_nodes, root_flows, STANDALONE_MAX_DEPTH)

    merged_slices = _merge_candidate_slices(candidate, slices)
    base_index = dict(candidate.get("registry_index") or {})
    base_index["max_depth"] = STANDALONE_MAX_DEPTH
    base_index["root_flows"] = root_flows
    norm_index = _normalize_registry_index(base_index, norm_nodes, max_depth=STANDALONE_MAX_DEPTH)

    meta_title = (candidate.get("meta") or {}).get("title") if isinstance(candidate.get("meta"), dict) else None
    title = str(candidate.get("title") or meta_title or "Archify Drill-Down")
    html_out = build_portal_shell(
        norm_index,
        merged_slices,
        norm_nodes,
        mode="embedded",
        title=title,
        doc_lang=doc_lang,
    )
    _log(
        f"rendered standalone drilldown: nodes={len(norm_nodes)} slices={len(merged_slices)} "
        f"bytes={len(html_out.encode('utf-8'))}"
    )
    return html_out
