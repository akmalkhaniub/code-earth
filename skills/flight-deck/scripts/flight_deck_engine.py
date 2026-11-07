#!/usr/bin/env python3
"""
Code Earth - Planetary Topographic Semantic Zoom Engine
Visualizes a codebase as a living, organic digital planet in a clean, modern light aesthetic:
- Organic Tectonic Continents with topographic elevation contours (no rectangular boxes!)
- Authentic File Extension Icon Badges (Python, TypeScript, JS, JSON, HTML, Markdown, etc.)
- Zero Annoying Wave Emissions: Calm, serene, and professional status indicators
- GIF-like interactive micro-sheen on hover / active state
- Ground Code View: Sleek IDE card preview on deep zoom
- Responsive header with live zoom percentage and active altitude indicator
- Interactive Radar / Minimap to never lose orientation
- Clamped camera bounds and "Fit to Screen" (cannot get lost off-screen!)
- Ambient In-Situ Telemetry Reticles (zero screen-blocking drawers)
- Distraction-free: bottom flight steps hidden by default in an optional toggle
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
            if f.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.md', '.html', '.css', '.go', '.rs', '.sh', '.yml', '.yaml')):
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

        elif rel_str.endswith(('.js', '.ts', '.jsx', '.tsx')):
            try:
                with open(abs_p, 'r', encoding='utf-8', errors='ignore') as fp:
                    for line in fp:
                        m = re.search(r"""(?:import|require)\s*\(?['"](\.[^'"]+)['"]""", line)
                        if m:
                            imp_sub = m.group(1)
                            resolved_dir = abs_p.parent
                            for cand_ext in ['', '.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.js']:
                                cand = (resolved_dir / (imp_sub + cand_ext)).resolve()
                                if cand.is_file():
                                    try:
                                        target_cand = str(cand.relative_to(repo_root)).replace('\\', '/')
                                        if target_cand != rel_str:
                                            dependencies[rel_str].add(target_cand)
                                            dependents[target_cand].add(rel_str)
                                            break
                                    except Exception:
                                        pass
            except Exception:
                pass

    return file_data, dependencies, dependents

def parse_transcript_events(transcript_path: Path, repo_root: Path):
    """Reconstructs the agent flight path from transcript.jsonl."""
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
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue

                tool_calls = entry.get("tool_calls", [])
                thinking = entry.get("thinking", "")
                thought_snip = (thinking[:140] + "...") if thinking else ""

                for tc in tool_calls:
                    fn = tc.get("name") or tc.get("tool") or ""
                    args = tc.get("args") or tc.get("arguments") or {}

                    target_file = None
                    action = "read"

                    if fn in ("write_file", "edit_file"):
                        target_file = args.get("Path") or args.get("path")
                        action = "edit"
                    elif fn == "read_file":
                        target_file = args.get("Path") or args.get("path")
                        action = "read"
                    elif fn == "run_command":
                        cmd = args.get("CommandLine", "") or args.get("command", "")
                        if "pytest" in cmd or "npm test" in cmd or "test" in cmd:
                            test_runs.append({"step": step_counter, "cmd": cmd, "status": "pass"})
                        steps.append({"step": step_counter, "type": "exec", "summary": f"run: {cmd[:60]}", "thought": thought_snip})
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

        ext = Path(fpath).suffix.lower().lstrip('.') or ("git" if "git" in fpath.lower() else "file")

        nodes.append({
            "id": fpath,
            "name": fpath.split('/')[-1],
            "ext": ext,
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
  <title>Code Earth - Planetary Semantic Architecture</title>
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

    <!-- Altitude, Live Zoom % & Camera Controls -->
    <div class="panel-glass rounded-full px-2.5 py-1.5 flex items-center gap-1 pointer-events-auto">
      <button id="btnOrbit" onclick="setAltitude(0.28)" class="px-2.5 py-1 rounded-full text-xs font-medium transition text-slate-700 hover:bg-slate-100" title="Planet Orbit">
        Orbit
      </button>
      <button id="btnContinent" onclick="setAltitude(0.85)" class="px-2.5 py-1 rounded-full text-xs font-medium transition text-slate-700 hover:bg-slate-100" title="Module Continent">
        Continent
      </button>
      <button id="btnCode" onclick="setAltitude(2.4)" class="px-2.5 py-1 rounded-full text-xs font-medium transition text-slate-700 hover:bg-slate-100" title="Ground Code View">
        Code
      </button>

      <div class="h-4 w-px bg-slate-200 mx-0.5"></div>

      <!-- Live Zoom Level Badge -->
      <span id="zoomPercent" class="font-mono text-[11px] font-bold text-slate-700 min-w-[38px] text-center px-1" title="Current Zoom">
        35%
      </span>

      <button onclick="zoomDelta(1.25)" class="w-7 h-7 flex items-center justify-center hover:bg-slate-100 text-slate-700 rounded-full text-xs font-bold" title="Zoom In">
        +
      </button>
      <button onclick="zoomDelta(0.8)" class="w-7 h-7 flex items-center justify-center hover:bg-slate-100 text-slate-700 rounded-full text-xs font-bold" title="Zoom Out">
        -
      </button>
      <button onclick="fitToScreen()" class="px-2 py-1 flex items-center gap-1 hover:bg-slate-100 text-slate-700 rounded-full text-xs font-medium" title="Center & Fit All to Screen">
        <span>🎯</span>
        <span class="hidden md:inline text-[11px]">Center</span>
      </button>
      <button onclick="toggleFullScreen()" class="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-white rounded-full text-xs font-medium transition ml-0.5" title="Fullscreen (F11)">
        ⛶
      </button>
    </div>
  </header>

  <!-- 100% CLEAN CANVAS -->
  <canvas id="earthCanvas" class="w-full h-full"></canvas>

  <!-- BOTTOM-LEFT RADAR / MINIMAP (Never lose your position on the planet) -->
  <div id="radarWidget" class="absolute bottom-3 left-3 z-20 panel-glass rounded-2xl p-2 shadow-lg pointer-events-auto flex flex-col gap-1 transition-opacity duration-200 hover:opacity-100 opacity-90">
    <div class="flex items-center justify-between px-1">
      <span class="text-[9px] font-bold uppercase tracking-wider text-slate-500">Radar</span>
      <span class="text-[8px] text-slate-400 font-mono">Click to Fly</span>
    </div>
    <canvas id="minimapCanvas" width="130" height="85" class="rounded-xl bg-slate-50/80 cursor-crosshair border border-slate-200"></canvas>
  </div>

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

    // ==========================================
    // AUTHENTIC FILE EXTENSION ICONS & BADGES
    // ==========================================
    const FILE_TYPES = {{
      py: {{
        key: "py",
        label: "PY",
        name: "Python Script",
        bg: "#0f172a",
        color: "#ffd438",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#0f172a"/><path d="M15.9 4c-5.2 0-4.9 2.3-4.9 2.3l.0 2.4h5v.8h-7.1c-3.4 0-6 2-6 6 0 3.9 2.6 5.8 6 5.8h1.8v-2.7c0-3 2.6-3 2.6-3h5c2.4 0 2.4-2.3 2.4-2.3v-4.5c0-4.4-2.3-4.8-4.8-4.8zm-1.4 1.8a.9.9 0 1 1 0 1.8.9.9 0 0 1 0-1.8z" fill="#387eb8"/><path d="M16.1 28c5.2 0 4.9-2.3 4.9-2.3l-.0-2.4h-5v-.8h7.1c3.4 0 6-2 6-6 0-3.9-2.6-5.8-6-5.8h-1.8v2.7c0 3-2.6 3-2.6 3h-5c-2.4 0-2.4 2.3-2.4 2.3v4.5c0 4.4 2.3 4.8 4.8 4.8zm1.4-1.8a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8z" fill="#ffd438"/></svg>`
      }},
      ts: {{
        key: "ts",
        label: "TS",
        name: "TypeScript Module",
        bg: "#3178c6",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#3178c6"/><text x="16" y="22" font-family="-apple-system, system-ui, sans-serif" font-weight="900" font-size="15" fill="#ffffff" text-anchor="middle">TS</text></svg>`
      }},
      tsx: {{
        key: "tsx",
        label: "TSX",
        name: "React TypeScript",
        bg: "#1e293b",
        color: "#61dafb",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#1e293b"/><text x="16" y="21" font-family="-apple-system, system-ui, sans-serif" font-weight="900" font-size="12" fill="#61dafb" text-anchor="middle">TSX</text></svg>`
      }},
      js: {{
        key: "js",
        label: "JS",
        name: "JavaScript Source",
        bg: "#f7df1e",
        color: "#000000",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#f7df1e"/><text x="16" y="22" font-family="-apple-system, system-ui, sans-serif" font-weight="900" font-size="15" fill="#000000" text-anchor="middle">JS</text></svg>`
      }},
      jsx: {{
        key: "jsx",
        label: "JSX",
        name: "React JavaScript",
        bg: "#20232a",
        color: "#61dafb",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#20232a"/><text x="16" y="21" font-family="-apple-system, system-ui, sans-serif" font-weight="900" font-size="12" fill="#61dafb" text-anchor="middle">JSX</text></svg>`
      }},
      json: {{
        key: "json",
        label: "{{}}",
        name: "JSON Configuration",
        bg: "#059669",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#059669"/><text x="16" y="22" font-family="monospace" font-weight="900" font-size="17" fill="#ffffff" text-anchor="middle">&#123;&#125;</text></svg>`
      }},
      md: {{
        key: "md",
        label: "MD",
        name: "Markdown Document",
        bg: "#0284c7",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#0284c7"/><path fill="#ffffff" d="M7 10v12h3.5v-7l3.5 4.5 3.5-4.5v7H21V10h-3.5l-3.5 4.5L10.5 10H7zm17.5 0v7h-2.5l4 5 4-5h-2.5v-7h-3z"/></svg>`
      }},
      html: {{
        key: "html",
        label: "<>",
        name: "HTML5 Document",
        bg: "#e34f26",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#e34f26"/><text x="16" y="22" font-family="-apple-system, system-ui, sans-serif" font-weight="900" font-size="12" fill="#ffffff" text-anchor="middle">&lt;/&gt;</text></svg>`
      }},
      css: {{
        key: "css",
        label: "#",
        name: "CSS3 Stylesheet",
        bg: "#2563eb",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#2563eb"/><text x="16" y="23" font-family="-apple-system, system-ui, sans-serif" font-weight="900" font-size="18" fill="#ffffff" text-anchor="middle">#</text></svg>`
      }},
      sh: {{
        key: "sh",
        label: ">_",
        name: "Shell Script",
        bg: "#0f172a",
        color: "#22c55e",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#0f172a"/><text x="16" y="22" font-family="monospace" font-weight="bold" font-size="16" fill="#22c55e" text-anchor="middle">&gt;_</text></svg>`
      }},
      yml: {{
        key: "yml",
        label: "YML",
        name: "YAML / Config",
        bg: "#7c3aed",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#7c3aed"/><text x="16" y="21" font-family="-apple-system, system-ui, sans-serif" font-weight="bold" font-size="11" fill="#ffffff" text-anchor="middle">YML</text></svg>`
      }},
      git: {{
        key: "git",
        label: "GIT",
        name: "Git Repository File",
        bg: "#f05032",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#f05032"/><circle cx="12" cy="12" r="2.5" fill="#ffffff"/><circle cx="12" cy="20" r="2.5" fill="#ffffff"/><circle cx="20" cy="16" r="2.5" fill="#ffffff"/><path d="M12 12v8M12 16h4a4 4 0 0 0 4-4" stroke="#ffffff" stroke-width="2" fill="none"/></svg>`
      }},
      rs: {{
        key: "rs",
        label: "RS",
        name: "Rust Source",
        bg: "#ea580c",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#ea580c"/><text x="16" y="22" font-family="-apple-system, system-ui, sans-serif" font-weight="900" font-size="14" fill="#ffffff" text-anchor="middle">RS</text></svg>`
      }},
      go: {{
        key: "go",
        label: "GO",
        name: "Go Source",
        bg: "#00add8",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#00add8"/><text x="16" y="22" font-family="-apple-system, system-ui, sans-serif" font-weight="900" font-size="14" fill="#ffffff" text-anchor="middle">GO</text></svg>`
      }},
      sql: {{
        key: "sql",
        label: "SQL",
        name: "Database SQL",
        bg: "#0284c7",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#0284c7"/><text x="16" y="22" font-family="-apple-system, system-ui, sans-serif" font-weight="900" font-size="12" fill="#ffffff" text-anchor="middle">SQL</text></svg>`
      }},
      image: {{
        key: "image",
        label: "IMG",
        name: "Image Asset",
        bg: "#db2777",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#db2777"/><circle cx="12" cy="12" r="3" fill="#ffffff"/><path d="M6 22l6-8 5 6 4-4 5 6H6z" fill="#ffffff"/></svg>`
      }},
      default: {{
        key: "default",
        label: "FILE",
        name: "Source File",
        bg: "#64748b",
        color: "#ffffff",
        svg: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" rx="7" fill="#64748b"/><path d="M11 8h7l5 5v11H11V8zm6 1v5h5" fill="#ffffff" stroke="#64748b" stroke-width="1.5"/></svg>`
      }}
    }};

    // Preload SVG Icon Images into fast canvas cache
    const iconImageCache = new Map();
    Object.entries(FILE_TYPES).forEach(([k, t]) => {{
      if (t.svg) {{
        const img = new Image();
        img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(t.svg);
        iconImageCache.set(k, img);
      }}
    }});

    function getFileType(filename) {{
      const lower = (filename || "").toLowerCase();
      const ext = lower.split('.').pop();
      if (['py', 'pyi', 'pyw', 'ipynb'].includes(ext)) return FILE_TYPES.py;
      if (ext === 'tsx') return FILE_TYPES.tsx;
      if (ext === 'ts') return FILE_TYPES.ts;
      if (ext === 'jsx') return FILE_TYPES.jsx;
      if (['js', 'mjs', 'cjs'].includes(ext)) return FILE_TYPES.js;
      if (['json', 'jsonl'].includes(ext)) return FILE_TYPES.json;
      if (['md', 'markdown'].includes(ext)) return FILE_TYPES.md;
      if (['html', 'htm'].includes(ext)) return FILE_TYPES.html;
      if (['css', 'scss', 'sass', 'less'].includes(ext)) return FILE_TYPES.css;
      if (['sh', 'bash', 'zsh', 'ps1', 'bat', 'cmd'].includes(ext)) return FILE_TYPES.sh;
      if (['yml', 'yaml', 'toml', 'env', 'ini'].includes(ext)) return FILE_TYPES.yml;
      if (lower.includes('git')) return FILE_TYPES.git;
      if (ext === 'rs') return FILE_TYPES.rs;
      if (ext === 'go') return FILE_TYPES.go;
      if (['sql', 'sqlite', 'db'].includes(ext)) return FILE_TYPES.sql;
      if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico'].includes(ext)) return FILE_TYPES.image;
      return FILE_TYPES.default;
    }}

    const canvas = document.getElementById("earthCanvas");
    const ctx = canvas.getContext("2d");
    const minimap = document.getElementById("minimapCanvas");
    const mmCtx = minimap.getContext("2d");

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    window.addEventListener("resize", () => {{
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      clampCamera();
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

    let worldMinX = Infinity, worldMaxX = -Infinity, worldMinY = Infinity, worldMaxY = -Infinity;

    // Generate organic coastline polygons with harmonic noise
    moduleList.forEach((modName, mi) => {{
      const col = mi % cols;
      const row = Math.floor(mi / cols);
      const cx = (col - cols / 2 + 0.5) * continentSpacingX;
      const cy = (row - Math.ceil(moduleList.length / cols) / 2 + 0.5) * continentSpacingY;

      const files = DATA.modules[modName];
      const baseRadius = Math.max(200, Math.sqrt(files.length) * 115);

      worldMinX = Math.min(worldMinX, cx - baseRadius);
      worldMaxX = Math.max(worldMaxX, cx + baseRadius);
      worldMinY = Math.min(worldMinY, cy - baseRadius);
      worldMaxY = Math.max(worldMaxY, cy + baseRadius);

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

    // Ensure fallback bounds if empty
    if (worldMinX === Infinity) {{
      worldMinX = -400; worldMaxX = 400; worldMinY = -300; worldMaxY = 300;
    }}

    let animTime = 0;

    // CAMERA CLAMPING: Prevents the world from ever going off screen!
    function clampCamera() {{
      const screenLeft = panX + worldMinX * scale;
      const screenRight = panX + worldMaxX * scale;
      const screenTop = panY + worldMinY * scale;
      const screenBottom = panY + worldMaxY * scale;

      const minMargin = 120;
      if (screenRight < minMargin) panX = minMargin - worldMaxX * scale;
      if (screenLeft > width - minMargin) panX = (width - minMargin) - worldMinX * scale;
      if (screenBottom < minMargin) panY = minMargin - worldMaxY * scale;
      if (screenTop > height - minMargin) panY = (height - minMargin) - worldMinY * scale;
    }}

    // UPDATE ZOOM & ACTIVE ALTITUDE INDICATOR
    function updateZoomUI() {{
      const zPill = document.getElementById("zoomPercent");
      if (zPill) zPill.textContent = Math.round(scale * 100) + "%";

      const bOrb = document.getElementById("btnOrbit");
      const bCont = document.getElementById("btnContinent");
      const bCode = document.getElementById("btnCode");

      if (bOrb && bCont && bCode) {{
        [bOrb, bCont, bCode].forEach(b => {{
          b.className = "px-2.5 py-1 rounded-full text-xs font-medium transition text-slate-700 hover:bg-slate-100";
        }});

        if (scale < 0.55) {{
          bOrb.className = "px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-900 text-white shadow-sm";
        }} else if (scale < 1.7) {{
          bCont.className = "px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-900 text-white shadow-sm";
        }} else {{
          bCode.className = "px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-900 text-white shadow-sm";
        }}
      }}
    }}

    // FIT TO SCREEN: Instantly frames all continents centered with comfort margin
    function fitToScreen() {{
      const pad = 140;
      const wSpan = (worldMaxX - worldMinX) + pad * 2;
      const hSpan = (worldMaxY - worldMinY) + pad * 2;
      const sX = width / wSpan;
      const sY = height / hSpan;
      scale = Math.min(Math.max(Math.min(sX, sY), 0.14), 1.0);

      const midX = (worldMinX + worldMaxX) / 2;
      const midY = (worldMinY + worldMaxY) / 2;
      panX = width / 2 - midX * scale;
      panY = height / 2 - midY * scale;

      activeNode = null;
      clampCamera();
      updateZoomUI();
    }}

    // Mouse Navigation
    canvas.addEventListener("wheel", (e) => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      const mouseX = e.clientX;
      const mouseY = e.clientY;

      const worldX = (mouseX - panX) / scale;
      const worldY = (mouseY - panY) / scale;

      scale = Math.min(Math.max(scale * zoomFactor, 0.12), 6.0);
      panX = mouseX - worldX * scale;
      panY = mouseY - worldY * scale;

      clampCamera();
      updateZoomUI();
    }});

    canvas.addEventListener("mousedown", (e) => {{
      isDragging = true;
      startX = e.clientX - panX;
      startY = e.clientY - panY;
    }});

    window.addEventListener("mousemove", (e) => {{
      if (isDragging) {{
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        clampCamera();
      }} else {{
        const worldX = (e.clientX - panX) / scale;
        const worldY = (e.clientY - panY) / scale;
        let found = null;

        for (const n of DATA.nodes) {{
          const pt = nodeCoords.get(n.id);
          if (!pt) continue;
          const distSq = (worldX - pt.x) ** 2 + (worldY - pt.y) ** 2;
          const hitRadius = scale > 1.7 ? 190 : 32;
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

    // Double-click to focus and zoom in
    canvas.addEventListener("dblclick", (e) => {{
      if (hoveredNode) {{
        const pt = nodeCoords.get(hoveredNode.id);
        if (pt) {{
          scale = 2.4;
          panX = width / 2 - pt.x * scale;
          panY = height / 2 - pt.y * scale;
          activeNode = hoveredNode;
          clampCamera();
          updateZoomUI();
        }}
      }} else {{
        fitToScreen();
      }}
    }});

    function setAltitude(s) {{
      scale = s;
      clampCamera();
      updateZoomUI();
    }}

    function zoomDelta(factor) {{
      scale = Math.min(Math.max(scale * factor, 0.12), 6.0);
      clampCamera();
      updateZoomUI();
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

    // RADAR / MINIMAP NAVIGATION
    minimap.addEventListener("click", (e) => {{
      const rect = minimap.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      const mmW = minimap.width;
      const mmH = minimap.height;

      const pad = 120;
      const wSpan = (worldMaxX - worldMinX) + pad * 2;
      const hSpan = (worldMaxY - worldMinY) + pad * 2;

      const worldTargetX = worldMinX - pad + (clickX / mmW) * wSpan;
      const worldTargetY = worldMinY - pad + (clickY / mmH) * hSpan;

      panX = width / 2 - worldTargetX * scale;
      panY = height / 2 - worldTargetY * scale;
      clampCamera();
    }});

    function renderRadar() {{
      mmCtx.clearRect(0, 0, minimap.width, minimap.height);

      const mmW = minimap.width;
      const mmH = minimap.height;
      const pad = 120;
      const wSpan = (worldMaxX - worldMinX) + pad * 2;
      const hSpan = (worldMaxY - worldMinY) + pad * 2;

      function toMmX(wx) {{ return ((wx - (worldMinX - pad)) / wSpan) * mmW; }}
      function toMmY(wy) {{ return ((wy - (worldMinY - pad)) / hSpan) * mmH; }}

      // Draw mini-continents
      continentLayout.forEach((cont) => {{
        const mx = toMmX(cont.cx);
        const my = toMmY(cont.cy);
        const mr = (cont.baseRadius / wSpan) * mmW;

        mmCtx.beginPath();
        mmCtx.arc(mx, my, Math.max(3, mr), 0, Math.PI * 2);
        mmCtx.fillStyle = cont.hasEpicenter ? "#fecdd3" : "#e2e8f0";
        mmCtx.fill();
        mmCtx.strokeStyle = cont.hasEpicenter ? "#f43f5e" : "#cbd5e1";
        mmCtx.lineWidth = 1;
        mmCtx.stroke();
      }});

      // Draw active viewport rectangle
      const leftW = (0 - panX) / scale;
      const rightW = (width - panX) / scale;
      const topW = (0 - panY) / scale;
      const bottomW = (height - panY) / scale;

      const vx = toMmX(leftW);
      const vy = toMmY(topW);
      const vw = toMmX(rightW) - vx;
      const vh = toMmY(bottomW) - vy;

      mmCtx.strokeStyle = "#0f172a";
      mmCtx.lineWidth = 1.5;
      mmCtx.strokeRect(vx, vy, vw, vh);

      mmCtx.fillStyle = "rgba(15, 23, 42, 0.08)";
      mmCtx.fillRect(vx, vy, vw, vh);
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
      // 3. AUTHENTIC FILE BADGES & CODE STRATA (Zero Annoying Waves!)
      // ==========================================
      DATA.nodes.forEach(node => {{
        const pt = nodeCoords.get(node.id);
        if (!pt) return;

        const isHovered = hoveredNode && hoveredNode.id === node.id;
        const isActive = activeNode && activeNode.id === node.id;
        const ftype = getFileType(node.name || node.id);
        const iconImg = iconImageCache.get(ftype.key);

        // GROUND CODE LEVEL (Scale >= 1.7)
        if (scale >= 1.7) {{
          ctx.save();
          ctx.translate(pt.x, pt.y);

          const cardW = 380;
          const cardH = 240;
          const halfW = cardW / 2;
          const halfH = cardH / 2;

          // Code Container (Clean white card with soft elevation shadow)
          ctx.fillStyle = "#ffffff";
          ctx.shadowColor = "rgba(15, 23, 42, 0.10)";
          ctx.shadowBlur = 22;
          ctx.shadowOffsetY = 6;
          ctx.beginPath();
          ctx.roundRect(-halfW, -halfH, cardW, cardH, 14);
          ctx.fill();
          ctx.shadowBlur = 0;
          ctx.shadowOffsetY = 0;

          // Border based on blast tier
          ctx.strokeStyle = isHovered || isActive ? "#0f172a" : (node.tier === 0 ? "#f43f5e" : (node.tier === 1 ? "#f59e0b" : "#e2e8f0"));
          ctx.lineWidth = Math.max(1.5, 2.0 / scale);
          ctx.stroke();

          // Header bar
          ctx.fillStyle = "#f8fafc";
          ctx.beginPath();
          ctx.roundRect(-halfW, -halfH, cardW, 40, [14, 14, 0, 0]);
          ctx.fill();
          ctx.strokeStyle = "#e2e8f0";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(-halfW, -halfH + 40);
          ctx.lineTo(halfW, -halfH + 40);
          ctx.stroke();

          // Header: File Extension Icon
          if (iconImg && iconImg.complete && iconImg.naturalWidth !== 0) {{
            ctx.drawImage(iconImg, -halfW + 12, -halfH + 8, 24, 24);
          }} else {{
            ctx.fillStyle = ftype.bg;
            ctx.beginPath();
            ctx.roundRect(-halfW + 12, -halfH + 8, 24, 24, 5);
            ctx.fill();
            ctx.fillStyle = ftype.color;
            ctx.font = "bold 10px -apple-system, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(ftype.label, -halfW + 24, -halfH + 24);
          }}

          // Header: File Name
          ctx.fillStyle = "#0f172a";
          ctx.font = "bold 13px -apple-system, sans-serif";
          ctx.textAlign = "left";
          ctx.fillText(node.name, -halfW + 44, -halfH + 25);

          // Header: Tier Status Pill
          const tierText = node.tier === 0 ? "⚡ EPICENTER" : (node.tier === 1 ? "▲ RIPPLE" : "✓ SAFE");
          const tierColor = node.tier === 0 ? "#e11d48" : (node.tier === 1 ? "#d97706" : "#059669");
          const tierBg = node.tier === 0 ? "#ffe4e6" : (node.tier === 1 ? "#fef3c7" : "#ecfdf5");
          ctx.fillStyle = tierBg;
          ctx.beginPath();
          ctx.roundRect(halfW - 95, -halfH + 11, 82, 18, 9);
          ctx.fill();
          ctx.fillStyle = tierColor;
          ctx.font = "bold 9px -apple-system, sans-serif";
          ctx.textAlign = "center";
          ctx.fillText(tierText, halfW - 54, -halfH + 23);

          // Code Lines
          ctx.font = "10px SFMono-Regular, Consolas, monospace";
          ctx.textAlign = "left";
          const lines = node.diffLines && node.diffLines.length ? node.diffLines.slice(0, 10) : (node.codeLines || []).slice(0, 10);
          let ly = -halfH + 60;

          lines.forEach(l => {{
            if (l.type === "add") {{
              ctx.fillStyle = "#ecfdf5";
              ctx.fillRect(-halfW + 10, ly - 9, cardW - 20, 15);
              ctx.fillStyle = "#047857";
              ctx.fillText(`+ ${{l.text.slice(0, 48)}}`, -halfW + 16, ly + 2);
            }} else if (l.type === "del") {{
              ctx.fillStyle = "#fff1f2";
              ctx.fillRect(-halfW + 10, ly - 9, cardW - 20, 15);
              ctx.fillStyle = "#be123c";
              ctx.fillText(`- ${{l.text.slice(0, 48)}}`, -halfW + 16, ly + 2);
            }} else {{
              ctx.fillStyle = "#475569";
              const txt = l.text !== undefined ? l.text : l;
              ctx.fillText(`  ${{String(txt).slice(0, 48)}}`, -halfW + 16, ly + 2);
            }}
            ly += 16;
          }});

          ctx.restore();
        }}
        // FILE BADGE / ICON LEVEL (Scale < 1.7)
        else {{
          ctx.save();
          ctx.translate(pt.x, pt.y);

          // Responsive badge size
          let size = scale < 0.55 ? 26 : 34;
          if (isHovered || isActive) size += 6;
          const half = size / 2;

          // Subtle shadow
          ctx.shadowColor = "rgba(15, 23, 42, 0.12)";
          ctx.shadowBlur = isHovered || isActive ? 14 : 6;
          ctx.shadowOffsetY = 2;

          // Badge Background
          ctx.fillStyle = ftype.bg;
          ctx.beginPath();
          ctx.roundRect(-half, -half, size, size, 7);
          ctx.fill();
          ctx.shadowBlur = 0;
          ctx.shadowOffsetY = 0;

          // File Extension SVG Icon / Glyph
          if (iconImg && iconImg.complete && iconImg.naturalWidth !== 0) {{
            const pad = 3;
            ctx.drawImage(iconImg, -half + pad, -half + pad, size - pad * 2, size - pad * 2);
          }} else {{
            ctx.fillStyle = ftype.color;
            ctx.font = `900 ${{Math.round(size * 0.40)}}px -apple-system, sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(ftype.label, 0, 0);
          }}

          // Blast Radius Border (Crisp, No wave emission!)
          let strokeColor = "rgba(255, 255, 255, 0.85)";
          let strokeWidth = 1.2;
          if (node.tier === 0) {{
            strokeColor = "#f43f5e"; // Rose Epicenter
            strokeWidth = 2.4;
          }} else if (node.tier === 1) {{
            strokeColor = "#f59e0b"; // Amber Ripple
            strokeWidth = 2.0;
          }} else if (isHovered || isActive) {{
            strokeColor = "#0f172a";
            strokeWidth = 1.8;
          }}
          ctx.strokeStyle = strokeColor;
          ctx.lineWidth = strokeWidth;
          ctx.stroke();

          // Corner Status Pip (No radiating continuous rings!)
          if (node.tier === 0) {{
            // Ruby Red Status Pip on top-right
            ctx.beginPath();
            ctx.arc(half - 2, -half + 2, 4.5, 0, Math.PI * 2);
            ctx.fillStyle = "#e11d48";
            ctx.fill();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }} else if (node.tier === 1) {{
            // Amber Pip on top-right
            ctx.beginPath();
            ctx.arc(half - 2, -half + 2, 4, 0, Math.PI * 2);
            ctx.fillStyle = "#ea580c";
            ctx.fill();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.2;
            ctx.stroke();
          }}

          // GIF-like Micro-Sheen on Hover / Active
          if (isHovered || isActive) {{
            const sheenT = (animTime * 1.4) % 2.2;
            if (sheenT < 1.1) {{
              ctx.save();
              ctx.beginPath();
              ctx.roundRect(-half, -half, size, size, 7);
              ctx.clip();
              const sx = -size + sheenT * size * 2.2;
              const grad = ctx.createLinearGradient(sx, -half, sx + 14, half);
              grad.addColorStop(0, "rgba(255, 255, 255, 0)");
              grad.addColorStop(0.5, "rgba(255, 255, 255, 0.45)");
              grad.addColorStop(1, "rgba(255, 255, 255, 0)");
              ctx.fillStyle = grad;
              ctx.fillRect(-half, -half, size, size);
              ctx.restore();
            }}
          }}

          // File Label Underneath
          if (scale > 0.45 || isHovered || isActive) {{
            ctx.fillStyle = isHovered || isActive ? "#0f172a" : "#334155";
            ctx.font = isHovered || isActive ? "600 12px -apple-system, sans-serif" : "500 11px -apple-system, sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(node.name, 0, half + 5);

            // Change pill if modified
            if (node.tier === 0 && (scale > 0.65 || isHovered)) {{
              const diffStr = (node.added > 0 || node.deleted > 0) ? `+${{node.added}} -${{node.deleted}}` : "EDITED";
              ctx.fillStyle = "#e11d48";
              ctx.font = "bold 9px -apple-system, sans-serif";
              ctx.fillText(diffStr, 0, half + 19);
            }}
          }}

          ctx.restore();
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
          ctx.arc(0, 0, 24, 0, Math.PI * 2);
          ctx.stroke();

          // Floating Telemetry Box
          const boxX = 32;
          const boxY = -48;
          ctx.fillStyle = "rgba(255, 255, 255, 0.98)";
          ctx.strokeStyle = "#cbd5e1";
          ctx.lineWidth = 1 / scale;
          ctx.shadowColor = "rgba(15, 23, 42, 0.08)";
          ctx.shadowBlur = 14;
          ctx.beginPath();
          ctx.roundRect(boxX, boxY, 175, 66, 8);
          ctx.fill();
          ctx.shadowBlur = 0;
          ctx.stroke();

          // Title & Extension Type
          ctx.fillStyle = "#0f172a";
          ctx.font = "bold 11px -apple-system, sans-serif";
          ctx.textAlign = "left";
          ctx.fillText(node.name, boxX + 10, boxY + 18);

          // Type descriptor
          ctx.fillStyle = "#64748b";
          ctx.font = "9px -apple-system, sans-serif";
          ctx.fillText(ftype.name, boxX + 10, boxY + 31);

          // Tier badge
          ctx.font = "bold 9px -apple-system, sans-serif";
          ctx.fillStyle = node.tier === 0 ? "#e11d48" : (node.tier === 1 ? "#ea580c" : "#0284c7");
          const tierLabel = node.tier === 0 ? "⚡ EPICENTER (ACTIVE EDIT)" : (node.tier === 1 ? "▲ RIPPLE ZONE" : "✓ SAFE BEDROCK");
          ctx.fillText(tierLabel, boxX + 10, boxY + 45);

          // Stats
          ctx.fillStyle = "#475569";
          let statText = "";
          if (node.added > 0 || node.deleted > 0) {{
            statText = `+${{node.added}} -${{node.deleted}} Diff | ${{node.inbound.length}} callers`;
          }} else if (node.tier === 0) {{
            statText = `Active Session Edit | ${{node.inbound.length}} callers`;
          }} else {{
            statText = `Clean Bedrock | ${{node.inbound.length}} callers`;
          }}
          ctx.fillText(statText, boxX + 10, boxY + 58);

          ctx.restore();
        }}
      }});

      ctx.restore();
      renderRadar();
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
          clampCamera();
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

    // Initial Fit-To-Screen on Launch
    fitToScreen();
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
