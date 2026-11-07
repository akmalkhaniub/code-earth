#!/usr/bin/env python3
"""
Code Earth - Planetary Topographic Semantic Zoom Engine
Visualizes a codebase as a living, organic digital planet in a clean, modern light aesthetic:
- Organic Tectonic Continents with topographic elevation contours (no rectangular boxes!)
- Seismic Epicenters with animated shockwaves and blast radius particle highways
- Responsive header that never clips on narrow screens
- Ambient In-Situ Telemetry Reticles (zero screen-blocking drawers)
- Distraction-free: bottom flight steps hidden by default in an optional toggle
- Topographic Code Strata etched directly into the bedrock on ground zoom
"""

import os
import sys
import json
import ast
import re
import argparse
import subprocess
from pathlib import Path
from collections import defaultdict

def get_git_diff_details(repo_root: Path):
    """Extracts git status, numstat, and diff hunks per file, with fallback for non-git workspaces."""
    files_info = {}
    is_git_repo = False
    try:
        check_git = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(repo_root), capture_output=True, text=True, check=False)
        is_git_repo = (check_git.returncode == 0 and "true" in check_git.stdout.strip())
    except Exception:
        is_git_repo = False

    if is_git_repo:
        try:
            st = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo_root), capture_output=True, text=True, check=False)
            if st.returncode == 0:
                for line in st.stdout.splitlines():
                    if len(line) >= 4:
                        status_code = line[:2].strip()
                        fpath = line[3:].strip().strip('"').replace('\\', '/')
                        files_info[fpath] = {
                            "status": status_code,
                            "added": 0,
                            "deleted": 0,
                            "diff_lines": []
                        }

            ns = subprocess.run(["git", "diff", "--numstat", "HEAD"], cwd=str(repo_root), capture_output=True, text=True, check=False)
            if ns.returncode == 0:
                for line in ns.stdout.splitlines():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        add, rem, fpath = parts[0], parts[1], parts[2].replace('\\', '/')
                        if fpath not in files_info:
                            files_info[fpath] = {"status": "M", "added": 0, "deleted": 0, "diff_lines": []}
                        files_info[fpath]["added"] = int(add) if add.isdigit() else 0
                        files_info[fpath]["deleted"] = int(rem) if rem.isdigit() else 0

            # Count lines for untracked files
            for fpath, meta in files_info.items():
                if meta["status"] == "??" and meta["added"] == 0:
                    target_file = repo_root / fpath
                    if target_file.exists():
                        try:
                            line_cnt = len(target_file.read_text(encoding='utf-8', errors='ignore').splitlines())
                            meta["added"] = line_cnt
                        except Exception:
                            pass

            for fpath in list(files_info.keys()):
                df = subprocess.run(["git", "diff", "-U3", "HEAD", "--", fpath], cwd=str(repo_root), capture_output=True, text=True, check=False)
                if df.returncode == 0 and df.stdout:
                    hunk_lines = []
                    for dl in df.stdout.splitlines()[:120]:
                        if dl.startswith('+') and not dl.startswith('+++'):
                            hunk_lines.append({"type": "add", "text": dl[1:]})
                        elif dl.startswith('-') and not dl.startswith('---'):
                            hunk_lines.append({"type": "del", "text": dl[1:]})
                        elif dl.startswith(' '):
                            hunk_lines.append({"type": "ctx", "text": dl[1:]})
                    files_info[fpath]["diff_lines"] = hunk_lines
        except Exception as e:
            print(f"[Warning] Git inspection: {e}", file=sys.stderr)

    return files_info, is_git_repo

def extract_ast_symbols_and_code(abs_path: Path, max_code_lines=100):
    """Extracts symbols and raw code lines for deep topographic zoom."""
    symbols = []
    code_lines = []
    
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as fp:
            raw_content = fp.read()

        raw_split = raw_content.splitlines()
        code_lines = [{"num": i + 1, "text": l} for i, l in enumerate(raw_split[:max_code_lines])]

        if abs_path.suffix == '.py':
            tree = ast.parse(raw_content, filename=str(abs_path))
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append({
                        "kind": "fn",
                        "name": node.name,
                        "line": getattr(node, 'lineno', 0),
                        "args": [a.arg for a in node.args.args]
                    })
                elif isinstance(node, ast.ClassDef):
                    symbols.append({
                        "kind": "class",
                        "name": node.name,
                        "line": getattr(node, 'lineno', 0),
                        "methods": [sub.name for sub in node.body if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    })
        elif abs_path.suffix in ('.js', '.ts', '.jsx', '.tsx'):
            fn_re = re.compile(r"""(?:function\s+([a-zA-Z0-9_$]+)|(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|class\s+([a-zA-Z0-9_$]+))""")
            for i, line in enumerate(raw_split[:max_code_lines]):
                m = fn_re.search(line)
                if m:
                    name = m.group(1) or m.group(2) or m.group(3)
                    kind = "class" if "class" in line else "fn"
                    symbols.append({"kind": kind, "name": name, "line": i + 1, "args": []})

    except Exception:
        pass

    return symbols, code_lines

def build_workspace_graph(repo_root: Path, max_files=200):
    """Discovers files and maps dependency imports."""
    dependencies = defaultdict(set)
    dependents = defaultdict(set)
    file_data = {}
    known_py_files = {}

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in {'.git', '.agents', '__pycache__', 'node_modules', '.venv', 'venv', '.gemini', 'dist', 'build', '.idea'}]
        for f in files:
            p = (Path(root) / f).resolve()
            rel_str = str(p.relative_to(repo_root)).replace('\\', '/')
            if f.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.md', '.html', '.css', '.go', '.rs')):
                if f.endswith('.py'):
                    known_py_files[p] = rel_str
                file_data[rel_str] = {"abs": p, "name": f}
            if len(file_data) >= max_files:
                break
        if len(file_data) >= max_files:
            break

    for rel_str, meta in file_data.items():
        abs_p = meta["abs"]
        if rel_str.endswith('.py'):
            try:
                with open(abs_p, 'r', encoding='utf-8', errors='ignore') as fp:
                    tree = ast.parse(fp.read(), filename=str(abs_p))
                for node in ast.walk(tree):
                    target_cand = None
                    if isinstance(node, ast.Import):
                        for a in node.names:
                            m_path = a.name.replace('.', '/')
                            for cand in [repo_root / f"{m_path}.py", repo_root / m_path / "__init__.py"]:
                                if cand.resolve() in known_py_files:
                                    target_cand = known_py_files[cand.resolve()]
                                    break
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        if node.level > 0:
                            cdir = abs_p.parent
                            for _ in range(node.level - 1):
                                cdir = cdir.parent
                            t_base = cdir / mod.replace('.', '/') if mod else cdir
                            for cand in [t_base.with_suffix('.py'), t_base / '__init__.py']:
                                if cand.resolve() in known_py_files:
                                    target_cand = known_py_files[cand.resolve()]
                                    break
                        else:
                            m_path = mod.replace('.', '/')
                            for cand in [repo_root / f"{m_path}.py", repo_root / m_path / "__init__.py"]:
                                if cand.resolve() in known_py_files:
                                    target_cand = known_py_files[cand.resolve()]
                                    break
                    if target_cand and target_cand != rel_str:
                        dependencies[rel_str].add(target_cand)
                        dependents[target_cand].add(rel_str)
            except Exception:
                pass

    return file_data, dependencies, dependents

def parse_transcript_events(transcript_path: Path, repo_root: Path):
    """Reconstructs the agent's flight path from transcript.jsonl."""
    steps = []
    file_events = defaultdict(list)
    test_runs = []

    if not transcript_path or not transcript_path.exists():
        return steps, file_events, test_runs

    step_counter = 1
    try:
        with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as fp:
            for line in fp:
                line = line.strip()
                if not line: continue
                try: record = json.loads(line)
                except Exception: continue

                tool_calls = record.get("tool_calls", [])
                thinking = record.get("thinking", "")
                thought_snip = thinking.strip().split("\n")[0][:120] if thinking else ""

                for tc in tool_calls:
                    fn = tc.get("name")
                    args = tc.get("args", {})
                    target_file = None
                    action = None

                    if fn == "read_file":
                        action = "read"
                        target_file = args.get("Path", "")
                    elif fn in ("write_file", "edit_file"):
                        action = "edit"
                        target_file = args.get("Path", "")
                    elif fn == "run_command":
                        cmd = args.get("CommandLine", "")
                        summary = args.get("toolSummary", cmd)
                        is_test = any(t in cmd.lower() for t in ["test", "pytest", "jest", "vitest"])
                        if is_test:
                            content = record.get("content", "")
                            passed = "FAILED" not in content and "ERROR" not in content
                            test_runs.append({"step": step_counter, "cmd": cmd, "passed": passed})
                        steps.append({"step": step_counter, "type": "command", "cmd": cmd, "summary": summary, "thought": thought_snip})
                        step_counter += 1
                        continue

                    if target_file:
                        try:
                            rel_target = str(Path(target_file).resolve().relative_to(repo_root)).replace('\\', '/')
                        except Exception:
                            rel_target = target_file.replace('\\', '/')

                        item = {"step": step_counter, "type": action, "file": rel_target, "thought": thought_snip}
                        steps.append(item)
                        file_events[rel_target].append(item)
                        step_counter += 1
    except Exception as e:
        print(f"[Warning] Transcript parsing: {e}", file=sys.stderr)

    return steps, file_events, test_runs

def compute_blast_tiers(modified_files, dependents, file_events):
    """0=Epicenter (modified), 1=Direct Ripple, 2=Transitive, 3=Inspected."""
    tier_map = {}
    tier_0 = set(modified_files.keys())
    for f, evs in file_events.items():
        if any(e["type"] == "edit" for e in evs):
            tier_0.add(f)

    for f in tier_0:
        tier_map[f] = 0

    tier_1 = set()
    for f in tier_0:
        for dep in dependents.get(f, []):
            if dep not in tier_map:
                tier_1.add(dep)
                tier_map[dep] = 1

    tier_2 = set()
    for f in tier_1:
        for dep in dependents.get(f, []):
            if dep not in tier_map:
                tier_2.add(dep)
                tier_map[dep] = 2

    for f in file_events:
        if f not in tier_map:
            tier_map[f] = 3

    return tier_map

def generate_code_earth_deck(repo_name, repo_root, file_data, tier_map, git_info, dependencies, dependents, steps, file_events, test_runs):
    """Generates the organic topographic Code Earth canvas visualization in a clean, modern light aesthetic."""

    included_files = set(tier_map.keys())
    if not included_files:
        included_files = set(list(file_data.keys())[:16])

    nodes = []
    modules = defaultdict(list)

    for fpath in included_files:
        abs_p = repo_root / fpath
        tier = tier_map.get(fpath, 4)
        g_data = git_info.get(fpath, {})
        diff_lines = g_data.get("diff_lines", [])
        symbols, code_lines = extract_ast_symbols_and_code(abs_p) if abs_p.exists() else ([], [])

        parts = fpath.split('/')
        mod = parts[0] if len(parts) > 1 else "(root)"
        if mod in ('src', 'app', 'lib', 'pkg') and len(parts) > 2:
            mod = f"{parts[0]}/{parts[1]}"
        modules[mod].append(fpath)

        nodes.append({
            "id": fpath,
            "name": fpath.split('/')[-1],
            "dir": '/'.join(fpath.split('/')[:-1]) or '.',
            "module": mod,
            "tier": tier,
            "added": g_data.get("added", 0),
            "deleted": g_data.get("deleted", 0),
            "status": g_data.get("status", "Clean"),
            "diffLines": diff_lines,
            "symbols": symbols,
            "codeLines": code_lines,
            "inbound": list(dependents.get(fpath, [])),
            "outbound": list(dependencies.get(fpath, [])),
            "events": file_events.get(fpath, [])
        })

    links = []
    for n in nodes:
        src = n["id"]
        for tgt in dependencies.get(src, []):
            if tgt in included_files:
                links.append({"source": src, "target": tgt})

    payload = {
        "repo": repo_name,
        "nodes": nodes,
        "links": links,
        "modules": dict(modules),
        "steps": steps,
        "testRuns": test_runs
    }

    payload_json = json.dumps(payload)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Code Earth - {repo_name}</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    body {{
      background-color: #f8fafc;
      color: #0f172a;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      overflow: hidden;
      user-select: none;
    }}
    canvas {{
      display: block;
      cursor: grab;
    }}
    canvas:active {{
      cursor: grabbing;
    }}
    .panel-glass {{
      background: rgba(255, 255, 255, 0.94);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(226, 232, 240, 0.95);
      box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.08), 0 2px 6px -1px rgba(15, 23, 42, 0.04);
    }}
    ::-webkit-scrollbar {{ width: 5px; }}
    ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 4px; }}
  </style>
</head>
<body class="w-screen h-screen">

  <!-- TOP RESPONSIVE HEADER BAR (Never clips offscreen) -->
  <header class="absolute top-3 left-3 right-3 z-20 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
    
    <!-- Title & Condition Badge -->
    <div class="panel-glass rounded-full px-4 py-2 flex items-center gap-3 pointer-events-auto max-w-full">
      <div class="flex items-center gap-2">
        <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_6px_#10b981]"></span>
        <span class="font-bold text-xs tracking-wider text-slate-900 uppercase">Code Earth</span>
        <span class="text-slate-300 text-xs">/</span>
        <span class="text-slate-600 text-xs font-mono truncate max-w-[140px]" title="{repo_name}">{repo_name}</span>
      </div>

      <div class="h-4 w-px bg-slate-200"></div>

      <!-- Quick Metrics -->
      <div class="flex items-center gap-3 text-xs">
        <div class="flex items-center gap-1.5" title="Direct Changes">
          <span class="w-2 h-2 rounded-full bg-rose-500"></span>
          <span class="font-bold text-rose-600" id="stat-epicenter">0</span>
          <span class="text-slate-500 text-[11px] hidden sm:inline">Epicenter</span>
        </div>
        <div class="flex items-center gap-1.5" title="Direct Dependents">
          <span class="w-2 h-2 rounded-full bg-amber-500"></span>
          <span class="font-bold text-amber-600" id="stat-ripple">0</span>
          <span class="text-slate-500 text-[11px] hidden sm:inline">Ripple</span>
        </div>
        <div class="flex items-center gap-1.5" title="Safe Modules">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span class="font-bold text-emerald-600" id="stat-safe">0</span>
          <span class="text-slate-500 text-[11px] hidden sm:inline">Safe</span>
        </div>
      </div>
    </div>

    <!-- Altitude & Zoom Toolbar -->
    <div class="panel-glass rounded-full px-2.5 py-1.5 flex items-center gap-1 pointer-events-auto">
      <button onclick="setAltitude(0.28)" class="px-2.5 py-1 hover:bg-slate-100 rounded-full text-slate-700 text-xs font-medium transition" title="Planet Orbit">
        Orbit
      </button>
      <button onclick="setAltitude(0.85)" class="px-2.5 py-1 hover:bg-slate-100 rounded-full text-slate-700 text-xs font-medium transition" title="Module Continent">
        Continent
      </button>
      <button onclick="setAltitude(2.8)" class="px-2.5 py-1 bg-slate-100 text-slate-900 rounded-full text-xs font-semibold transition" title="Ground Code View">
        Code
      </button>
      <div class="h-4 w-px bg-slate-200 mx-0.5"></div>
      <button onclick="zoomDelta(1.25)" class="w-7 h-7 flex items-center justify-center hover:bg-slate-100 text-slate-700 rounded-full text-xs font-bold" title="Zoom In">
        +
      </button>
      <button onclick="zoomDelta(0.8)" class="w-7 h-7 flex items-center justify-center hover:bg-slate-100 text-slate-700 rounded-full text-xs font-bold" title="Zoom Out">
        -
      </button>
      <button onclick="resetCamera()" class="w-7 h-7 flex items-center justify-center hover:bg-slate-100 text-slate-700 rounded-full text-xs" title="Reset View">
        ↺
      </button>
      <button onclick="toggleFullScreen()" class="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-white rounded-full text-xs font-medium transition ml-1" title="Fullscreen (F11)">
        ⛶
      </button>
    </div>
  </header>

  <!-- 100% CLEAN CANVAS -->
  <canvas id="earthCanvas" class="w-full h-full"></canvas>

  <!-- OPTIONAL FLOATING DRAWER FOR AGENT FLIGHT PATH (Hidden by default, zero clutter) -->
  <aside id="historyDrawer" class="fixed bottom-14 right-4 max-w-sm w-full panel-glass rounded-2xl p-4 shadow-2xl transition-all duration-300 translate-y-[200%] pointer-events-auto z-30">
    <div class="flex items-center justify-between pb-2 border-b border-slate-200">
      <div class="flex items-center gap-2">
        <span class="text-xs font-bold uppercase tracking-wider text-slate-800">Flight Path Replay</span>
        <span id="stepCount" class="text-[11px] font-mono text-slate-500">0 / 0</span>
      </div>
      <button onclick="toggleHistoryDrawer()" class="text-slate-400 hover:text-slate-700 text-sm p-1">✕</button>
    </div>
    
    <div class="py-3">
      <div class="flex items-center gap-2 mb-2">
        <span id="flightStep" class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono text-[10px] font-bold">Step 1</span>
        <span id="flightAction" class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 uppercase">IDLE</span>
      </div>
      <p id="flightThought" class="text-xs text-slate-600 line-clamp-2">Replaying agent actions across repository...</p>
    </div>

    <div class="flex items-center gap-3 pt-1">
      <button id="btnPlay" onclick="togglePlay()" class="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs transition hover:bg-slate-800">
        ▶
      </button>
      <input id="timeline" type="range" min="0" max="1" value="0" step="1" 
             class="flex-1 h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-900 focus:outline-none">
      <button onclick="stepDelta(-1)" class="p-1 hover:text-slate-900 text-slate-500 text-xs">◀</button>
      <button onclick="stepDelta(1)" class="p-1 hover:text-slate-900 text-slate-500 text-xs">▶</button>
    </div>
  </aside>

  <!-- BOTTOM STATUS PILL & HISTORY TOGGLE (Minimalist, unobtrusive) -->
  <footer class="absolute bottom-3 right-4 z-20 pointer-events-none">
    <button onclick="toggleHistoryDrawer()" class="panel-glass rounded-full px-3.5 py-1.5 text-xs text-slate-700 font-medium hover:bg-white transition flex items-center gap-1.5 pointer-events-auto shadow-md">
      <span>⏱️</span>
      <span>Flight History</span>
    </button>
  </footer>

  <script>
    const DATA = {payload_json};

    const canvas = document.getElementById("earthCanvas");
    const ctx = canvas.getContext("2d");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    window.addEventListener("resize", () => {{
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    }});

    // Camera State
    let scale = 0.35;
    let panX = width / 2;
    let panY = height / 2;
    let isDragging = false;
    let startX = 0, startY = 0;
    let hoveredNode = null;
    let activeNode = null;

    // Timeline State
    let currentStepIdx = 0;
    let isPlaying = false;
    let playInterval = null;

    // Stats
    const epCount = DATA.nodes.filter(n => n.tier === 0).length;
    const ripCount = DATA.nodes.filter(n => n.tier === 1 || n.tier === 2).length;
    const safeCount = DATA.nodes.filter(n => n.tier >= 3).length;
    document.getElementById("stat-epicenter").textContent = epCount;
    document.getElementById("stat-ripple").textContent = ripCount;
    document.getElementById("stat-safe").textContent = safeCount;

    // Topographic Continents Layout
    const moduleList = Object.keys(DATA.modules);
    const continentLayout = new Map();
    const nodeCoords = new Map();

    const cols = Math.ceil(Math.sqrt(moduleList.length || 1));
    const continentSpacingX = 900;
    const continentSpacingY = 750;

    // Generate organic coastline polygons with harmonic noise
    moduleList.forEach((modName, mi) => {{
      const col = mi % cols;
      const row = Math.floor(mi / cols);
      const cx = (col - cols / 2 + 0.5) * continentSpacingX;
      const cy = (row - Math.ceil(moduleList.length / cols) / 2 + 0.5) * continentSpacingY;

      const files = DATA.modules[modName];
      const baseRadius = Math.max(200, Math.sqrt(files.length) * 115);

      const numPoints = 32;
      const coastlinePoints = [];
      for (let i = 0; i < numPoints; i++) {{
        const theta = (i / numPoints) * Math.PI * 2;
        const rNoise = baseRadius * (1.0 + 0.12 * Math.sin(theta * 3 + mi) + 0.06 * Math.cos(theta * 5 - mi * 2));
        coastlinePoints.push({{
          x: cx + Math.cos(theta) * rNoise,
          y: cy + Math.sin(theta) * rNoise
        }});
      }}

      continentLayout.set(modName, {{
        cx, cy, baseRadius, points: coastlinePoints,
        hasEpicenter: files.some(f => {{
          const n = DATA.nodes.find(node => node.id === f);
          return n && n.tier === 0;
        }})
      }});

      files.forEach((fpath, fi) => {{
        const angle = (fi / files.length) * Math.PI * 2 + (mi * 0.4);
        const dist = Math.min(baseRadius - 60, (fi + 1) * 50);
        nodeCoords.set(fpath, {{
          x: cx + Math.cos(angle) * dist,
          y: cy + Math.sin(angle) * dist
        }});
      }});
    }});

    let animTime = 0;

    // Mouse Navigation
    canvas.addEventListener("wheel", (e) => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      const mouseX = e.clientX;
      const mouseY = e.clientY;

      const worldX = (mouseX - panX) / scale;
      const worldY = (mouseY - panY) / scale;

      scale = Math.min(Math.max(scale * zoomFactor, 0.12), 7.0);
      panX = mouseX - worldX * scale;
      panY = mouseY - worldY * scale;
    }});

    canvas.addEventListener("mousedown", (e) => {{
      isDragging = true;
      startX = e.clientX - panX;
      startY = e.clientY - panY;
    }});

    window.addEventListener("mousemove", (e) => {{
      if (isDragging) {{
        panX += e.clientX - startX;
        panY += e.clientY - startY;
      }} else {{
        const worldX = (e.clientX - panX) / scale;
        const worldY = (e.clientY - panY) / scale;
        let found = null;

        for (const n of DATA.nodes) {{
          const pt = nodeCoords.get(n.id);
          if (!pt) continue;
          const distSq = (worldX - pt.x) ** 2 + (worldY - pt.y) ** 2;
          const hitRadius = scale > 1.5 ? 90 : 25;
          if (distSq <= hitRadius ** 2) {{
            found = n;
            break;
          }}
        }}

        hoveredNode = found;
        canvas.style.cursor = hoveredNode ? "pointer" : (isDragging ? "grabbing" : "grab");
      }}
    }});

    window.addEventListener("mouseup", () => {{
      isDragging = false;
    }});

    canvas.addEventListener("click", () => {{
      if (hoveredNode) {{
        activeNode = activeNode === hoveredNode ? null : hoveredNode;
      }} else {{
        activeNode = null;
      }}
    }});

    function setAltitude(s) {{
      scale = s;
    }}

    function zoomDelta(factor) {{
      scale = Math.min(Math.max(scale * factor, 0.12), 7.0);
    }}

    function resetCamera() {{
      scale = 0.35;
      panX = width / 2;
      panY = height / 2;
      activeNode = null;
    }}

    function toggleFullScreen() {{
      if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen().catch(() => {{
          window.open(window.location.href, '_blank');
        }});
      }} else if (document.exitFullscreen) {{
        document.exitFullscreen();
      }}
    }}

    // History Drawer Toggle
    let historyOpen = false;
    function toggleHistoryDrawer() {{
      historyOpen = !historyOpen;
      const drw = document.getElementById("historyDrawer");
      if (historyOpen) {{
        drw.classList.remove("translate-y-[200%]");
      }} else {{
        drw.classList.add("translate-y-[200%]");
      }}
    }}

    // MAIN RENDER LOOP (60fps, Clean Light Aesthetic)
    function draw() {{
      animTime += 0.025;
      ctx.clearRect(0, 0, width, height);

      // Background Subtle Canvas
      ctx.fillStyle = "#f8fafc";
      ctx.fillRect(0, 0, width, height);

      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(scale, scale);

      // ==========================================
      // 1. ORGANIC TECTONIC CONTINENTS (Light Paper Bedrock)
      // ==========================================
      continentLayout.forEach((cont, modName) => {{
        const pts = cont.points;
        if (!pts.length) return;

        // Shelf Halo
        const shelfGrad = ctx.createRadialGradient(cont.cx, cont.cy, cont.baseRadius * 0.3, cont.cx, cont.cy, cont.baseRadius * 1.25);
        shelfGrad.addColorStop(0, cont.hasEpicenter ? "rgba(254, 226, 226, 0.6)" : "rgba(241, 245, 249, 0.8)");
        shelfGrad.addColorStop(1, "rgba(248, 250, 252, 0)");
        ctx.fillStyle = shelfGrad;
        ctx.beginPath();
        ctx.arc(cont.cx, cont.cy, cont.baseRadius * 1.25, 0, Math.PI * 2);
        ctx.fill();

        // Landmass Bedrock (Pure Clean White with Drop Shadow)
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) {{
          const prev = pts[i - 1];
          const curr = pts[i];
          const mx = (prev.x + curr.x) / 2;
          const my = (prev.y + curr.y) / 2;
          ctx.quadraticCurveTo(prev.x, prev.y, mx, my);
        }}
        ctx.closePath();
        ctx.fillStyle = "#ffffff";
        ctx.shadowColor = "rgba(15, 23, 42, 0.06)";
        ctx.shadowBlur = 24;
        ctx.shadowOffsetY = 4;
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.shadowOffsetY = 0;

        // Clean Coastline Border
        ctx.strokeStyle = cont.hasEpicenter ? "#fda4af" : "#cbd5e1";
        ctx.lineWidth = 1.8 / scale;
        ctx.stroke();

        // Delicate Elevation Contours
        [0.78, 0.55, 0.35].forEach((ratio, idx) => {{
          ctx.beginPath();
          for (let i = 0; i < pts.length; i++) {{
            const p = pts[i];
            const px = cont.cx + (p.x - cont.cx) * ratio;
            const py = cont.cy + (p.y - cont.cy) * ratio;
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          }}
          ctx.closePath();
          ctx.strokeStyle = cont.hasEpicenter ? 
            `rgba(244, 63, 94, ${{0.14 - idx * 0.03}})` : 
            `rgba(203, 213, 225, ${{0.4 - idx * 0.1}})`;
          ctx.lineWidth = 1 / scale;
          ctx.stroke();
        }});

        // Continent Name
        if (scale < 1.4) {{
          ctx.fillStyle = cont.hasEpicenter ? "#be123c" : "#334155";
          ctx.font = `700 ${{Math.max(13, 19)}}px -apple-system, system-ui, sans-serif`;
          ctx.textAlign = "center";
          ctx.fillText(`⯎ ${{modName.toUpperCase()}}`, cont.cx, cont.cy - cont.baseRadius - 14);
        }}
      }});

      // ==========================================
      // 2. DEPENDENCY RIVERS & SUBTLE PULSES
      // ==========================================
      DATA.links.forEach(l => {{
        const src = nodeCoords.get(l.source);
        const tgt = nodeCoords.get(l.target);
        if (!src || !tgt) return;

        const srcNode = DATA.nodes.find(n => n.id === l.source);
        const isEpicenterEdge = srcNode && srcNode.tier === 0;

        const midX = (src.x + tgt.x) / 2 - (tgt.y - src.y) * 0.15;
        const midY = (src.y + tgt.y) / 2 + (tgt.x - src.x) * 0.15;

        ctx.strokeStyle = isEpicenterEdge ? "rgba(244, 63, 94, 0.35)" : "rgba(203, 213, 225, 0.7)";
        ctx.lineWidth = Math.max(1, 1.4 / scale);
        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.quadraticCurveTo(midX, midY, tgt.x, tgt.y);
        ctx.stroke();

        // Flowing energy particle
        const t = (animTime * 0.5) % 1.0;
        const px = (1 - t) ** 2 * src.x + 2 * (1 - t) * t * midX + t ** 2 * tgt.x;
        const py = (1 - t) ** 2 * src.y + 2 * (1 - t) * t * midY + t ** 2 * tgt.y;

        ctx.beginPath();
        ctx.arc(px, py, isEpicenterEdge ? 3 : 2, 0, Math.PI * 2);
        ctx.fillStyle = isEpicenterEdge ? "#e11d48" : "#0284c7";
        ctx.fill();
      }});

      // ==========================================
      // 3. SEISMIC BEACONS & CODE STRATA
      // ==========================================
      DATA.nodes.forEach(node => {{
        const pt = nodeCoords.get(node.id);
        if (!pt) return;

        const isHovered = hoveredNode && hoveredNode.id === node.id;
        const isActive = activeNode && activeNode.id === node.id;

        let beaconColor = "#0284c7"; // Clean Azure
        if (node.tier === 0) beaconColor = "#e11d48"; // Epicenter Rose
        else if (node.tier === 1) beaconColor = "#ea580c"; // Ripple Tangerine
        else if (node.tier === 2) beaconColor = "#d97706"; // Transitive Amber

        // Shockwave rings for Epicenter
        if (node.tier === 0) {{
          for (let w = 0; w < 3; w++) {{
            const waveProgress = ((animTime * 0.7 + w * 0.33) % 1.0);
            const waveRadius = 12 + waveProgress * 85;
            const waveOpacity = (1.0 - waveProgress) * 0.45;

            ctx.beginPath();
            ctx.arc(pt.x, pt.y, waveRadius, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(225, 29, 72, ${{waveOpacity}})`;
            ctx.lineWidth = 1.8 / scale;
            ctx.stroke();
          }}
        }}

        // Ground Code Level (Scale >= 1.8)
        if (scale >= 1.8) {{
          ctx.save();
          ctx.translate(pt.x, pt.y);

          // Code Container (Clean white card)
          ctx.fillStyle = "#ffffff";
          ctx.shadowColor = "rgba(15, 23, 42, 0.08)";
          ctx.shadowBlur = 18;
          ctx.shadowOffsetY = 4;
          ctx.beginPath();
          ctx.arc(0, 0, 160, 0, Math.PI * 2);
          ctx.fill();
          ctx.shadowBlur = 0;

          ctx.strokeStyle = isHovered || isActive ? "#0f172a" : (node.tier === 0 ? "#fda4af" : "#e2e8f0");
          ctx.lineWidth = 1.5 / scale;
          ctx.stroke();

          // Title
          ctx.fillStyle = "#0f172a";
          ctx.font = "bold 13px -apple-system, sans-serif";
          ctx.textAlign = "center";
          ctx.fillText(node.name, 0, -125);

          // Lines
          ctx.font = "10px SFMono-Regular, Consolas, monospace";
          ctx.textAlign = "left";
          const lines = node.diffLines && node.diffLines.length ? node.diffLines.slice(0, 11) : (node.codeLines || []).slice(0, 11);
          let ly = -95;

          lines.forEach(l => {{
            if (l.type === "add") {{
              ctx.fillStyle = "#ecfdf5";
              ctx.fillRect(-135, ly - 9, 270, 14);
              ctx.fillStyle = "#047857";
              ctx.fillText(`+ ${{l.text.slice(0, 36)}}`, -130, ly + 2);
            }} else if (l.type === "del") {{
              ctx.fillStyle = "#fff1f2";
              ctx.fillRect(-135, ly - 9, 270, 14);
              ctx.fillStyle = "#be123c";
              ctx.fillText(`- ${{l.text.slice(0, 36)}}`, -130, ly + 2);
            }} else {{
              ctx.fillStyle = "#475569";
              const txt = l.text !== undefined ? l.text : l;
              ctx.fillText(`  ${{String(txt).slice(0, 36)}}`, -130, ly + 2);
            }}
            ly += 16;
          }});

          ctx.restore();
        }}
        // Beacon Node (Scale < 1.8)
        else {{
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, isHovered || isActive ? 12 : 8, 0, Math.PI * 2);
          ctx.fillStyle = beaconColor;
          ctx.fill();

          if (scale > 0.55 || isHovered || isActive) {{
            ctx.fillStyle = isHovered || isActive ? "#0f172a" : "#475569";
            ctx.font = isHovered || isActive ? "600 12px -apple-system, sans-serif" : "11px -apple-system, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(node.name, pt.x, pt.y + 19);
          }}
        }}

        // ==========================================
        // 4. RETICLE TELEMETRY HALO (In-situ, Clean White Card)
        // ==========================================
        if (isHovered || isActive) {{
          ctx.save();
          ctx.translate(pt.x, pt.y);

          // Targeting Ring
          ctx.strokeStyle = "#0f172a";
          ctx.lineWidth = 1.4 / scale;
          ctx.beginPath();
          ctx.arc(0, 0, 20, 0, Math.PI * 2);
          ctx.stroke();

          // Floating Telemetry Box
          const boxX = 30;
          const boxY = -42;
          ctx.fillStyle = "rgba(255, 255, 255, 0.98)";
          ctx.strokeStyle = "#cbd5e1";
          ctx.lineWidth = 1 / scale;
          ctx.shadowColor = "rgba(15, 23, 42, 0.08)";
          ctx.shadowBlur = 14;
          ctx.beginPath();
          ctx.roundRect(boxX, boxY, 155, 58, 8);
          ctx.fill();
          ctx.shadowBlur = 0;
          ctx.stroke();

          // Title
          ctx.fillStyle = "#0f172a";
          ctx.font = "bold 11px -apple-system, sans-serif";
          ctx.textAlign = "left";
          ctx.fillText(node.name, boxX + 10, boxY + 18);

          // Tier badge
          ctx.font = "10px -apple-system, sans-serif";
          ctx.fillStyle = node.tier === 0 ? "#e11d48" : (node.tier === 1 ? "#ea580c" : "#0284c7");
          const tierLabel = node.tier === 0 ? "⚡ EPICENTER" : (node.tier === 1 ? "▲ RIPPLE ZONE" : "✓ SAFE NODE");
          ctx.fillText(tierLabel, boxX + 10, boxY + 33);

          // Stats
          ctx.fillStyle = "#64748b";
          let statText = "";
          if (node.added > 0 || node.deleted > 0) {{
            statText = `+${{node.added}} -${{node.deleted}} Diff | ${{node.inbound.length}} callers`;
          }} else if (node.tier === 0) {{
            statText = `Active Session Edit | ${{node.inbound.length}} callers`;
          }} else {{
            statText = `Clean Bedrock | ${{node.inbound.length}} callers`;
          }}
          ctx.fillText(statText, boxX + 10, boxY + 47);

          ctx.restore();
        }}
      }});

      ctx.restore();
      requestAnimationFrame(draw);
    }}

    // Timeline Scrubber
    const timeline = document.getElementById("timeline");
    const stepCount = document.getElementById("stepCount");
    const flightThought = document.getElementById("flightThought");
    const flightStep = document.getElementById("flightStep");
    const flightAction = document.getElementById("flightAction");

    timeline.max = Math.max(0, DATA.steps.length - 1);
    stepCount.textContent = DATA.steps.length ? `1 / ${{DATA.steps.length}}` : "0 / 0";

    function setStep(idx) {{
      if (!DATA.steps.length) return;
      currentStepIdx = Math.max(0, Math.min(idx, DATA.steps.length - 1));
      timeline.value = currentStepIdx;
      stepCount.textContent = `${{currentStepIdx + 1}} / ${{DATA.steps.length}}`;

      const st = DATA.steps[currentStepIdx];
      if (st) {{
        flightStep.textContent = `Step ${{st.step}}`;
        flightAction.textContent = st.type.toUpperCase();
        flightThought.textContent = st.thought || (st.file ? `Targeted ${{st.file}}` : st.summary || "Agent working...");

        if (st.file && nodeCoords.has(st.file)) {{
          const pt = nodeCoords.get(st.file);
          panX = width / 2 - pt.x * scale;
          panY = height / 2 - pt.y * scale;
          const nodeObj = DATA.nodes.find(n => n.id === st.file);
          if (nodeObj) activeNode = nodeObj;
        }}
      }}
    }}

    timeline.addEventListener("input", (e) => setStep(parseInt(e.target.value, 10)));
    function stepDelta(d) {{ setStep(currentStepIdx + d); }}

    function togglePlay() {{
      isPlaying = !isPlaying;
      document.getElementById("btnPlay").textContent = isPlaying ? "⏸" : "▶";
      if (isPlaying) {{
        playInterval = setInterval(() => {{
          if (currentStepIdx >= DATA.steps.length - 1) setStep(0);
          else setStep(currentStepIdx + 1);
        }}, 1400);
      }} else {{
        clearInterval(playInterval);
      }}
    }}

    requestAnimationFrame(draw);
    if (DATA.steps.length) setStep(0);
  </script>
</body>
</html>
"""
    return html

def main():
    parser = argparse.ArgumentParser(description="Code Earth - Topographic Semantic Zoom Engine")
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("--transcript", default=None)
    parser.add_argument("--output", default="flight_deck.html")
    args = parser.parse_args()

    repo_root = Path(args.workspace).resolve()
    print(f"[*] Planetary scan of: {repo_root}")

    git_info, is_git = get_git_diff_details(repo_root)
    file_data, dependencies, dependents = build_workspace_graph(repo_root)

    transcript_path = None
    if args.transcript:
        transcript_path = Path(args.transcript).resolve()
    else:
        home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME", ""))
        brain_dir = home / ".gemini" / "antigravity" / "brain"
        if brain_dir.exists():
            for conv in sorted(brain_dir.iterdir(), key=os.path.getmtime, reverse=True):
                cand = conv / ".system_generated" / "logs" / "transcript.jsonl"
                if cand.exists():
                    transcript_path = cand
                    break

    steps, file_events, test_runs = parse_transcript_events(transcript_path, repo_root)
    tier_map = compute_blast_tiers(git_info, dependents, file_events)

    deck_html = generate_code_earth_deck(
        repo_name=repo_root.name,
        repo_root=repo_root,
        file_data=file_data,
        tier_map=tier_map,
        git_info=git_info,
        dependencies=dependencies,
        dependents=dependents,
        steps=steps,
        file_events=file_events,
        test_runs=test_runs
    )

    out_p = Path(args.output).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as fp:
        fp.write(deck_html)

    print(f"[+] Code Earth planetary visualizer generated at: {out_p}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
