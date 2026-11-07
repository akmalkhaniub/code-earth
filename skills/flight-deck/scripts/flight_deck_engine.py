#!/usr/bin/env python3
"""
Code Earth - Unified Multi-Perspective Visualizer & Command Deck
Features 4 Switchable Architectural Views:
1. 🗺️ Topographic Continents: Organic elevation contours & file extension badges
2. 🌍 3D Orbital Globe: Spherical 3D planet with latitude/longitude mesh & coordinate beacons
3. 🏙️ 2.5D Code City: Isometric extruded skyscrapers (height = LOC, rooftops = file emblems)
4. 🕸️ Neural Organic Graph: Force-directed dependency constellations & flowing energy cables

Plus Linear-Grade Productivity Shell:
- Command Palette (Cmd+K / /): Instant fuzzy search & fly-to navigation
- Left Collapsible File Tree Explorer: Folder hierarchy with blast radius badges
- Right Slide-Out Diff & Telemetry Inspector: Clickable caller graph & line-by-line diffs
- Instant Theme Switcher: Light (Clean Paper) ↔ Dark (Deep Space Obsidian)
- Minimalist Bottom Flight Path Replay: Step scrubber with agent reasoning
"""

import os
import sys
import json
import ast
import re
import math
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
    """Generates the multi-perspective Code Earth workspace visualizer with 4 switchable views."""

    included_files = set(tier_map.keys())
    if not included_files:
        included_files = set(list(file_data.keys())[:24])

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
            "loc": len(code_lines) or 25,
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
  <title>Code Earth - Multi-Perspective Visualizer</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {{
      --bg-page: #f8fafc;
      --text-primary: #0f172a;
      --text-secondary: #475569;
      --panel-glass: rgba(255, 255, 255, 0.94);
      --panel-border: rgba(226, 232, 240, 0.95);
      --shadow-elevation: 0 4px 20px -2px rgba(15, 23, 42, 0.08), 0 2px 6px -1px rgba(15, 23, 42, 0.04);
      --accent-active: #0f172a;
      --accent-active-text: #ffffff;
      --radar-bg: rgba(248, 250, 252, 0.9);
      --code-bg: #f8fafc;
      --diff-add-bg: #ecfdf5;
      --diff-add-text: #047857;
      --diff-del-bg: #fff1f2;
      --diff-del-text: #be123c;
    }}
    body.theme-dark {{
      --bg-page: #090d16;
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --panel-glass: rgba(15, 23, 42, 0.92);
      --panel-border: rgba(51, 65, 85, 0.85);
      --shadow-elevation: 0 6px 24px -2px rgba(0, 0, 0, 0.45);
      --accent-active: #38bdf8;
      --accent-active-text: #090d16;
      --radar-bg: rgba(15, 23, 42, 0.95);
      --code-bg: #0b0f19;
      --diff-add-bg: rgba(6, 78, 59, 0.35);
      --diff-add-text: #34d399;
      --diff-del-bg: rgba(136, 19, 55, 0.35);
      --diff-del-text: #fb7185;
    }}
    body {{
      background-color: var(--bg-page);
      color: var(--text-primary);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      overflow: hidden;
      user-select: none;
      transition: background-color 0.25s ease, color 0.25s ease;
    }}
    canvas {{
      display: block;
      cursor: grab;
    }}
    canvas:active {{
      cursor: grabbing;
    }}
    .panel-glass {{
      background: var(--panel-glass);
      backdrop-filter: blur(14px);
      border: 1px solid var(--panel-border);
      box-shadow: var(--shadow-elevation);
    }}
    .view-btn.active {{
      background-color: var(--accent-active);
      color: var(--accent-active-text);
      font-weight: 600;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    ::-webkit-scrollbar {{ width: 5px; }}
    ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 4px; }}
    body.theme-dark ::-webkit-scrollbar-thumb {{ background: #334155; }}
  </style>
</head>
<body class="w-screen h-screen">

  <!-- ======================================================== -->
  <!-- TOP UNIFIED COMMAND HEADER (Responsive & Auto-Wrapping)  -->
  <!-- ======================================================== -->
  <header class="absolute top-3 left-3 right-3 z-30 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
    
    <!-- Left: Brand & Telemetry Condition Badges -->
    <div class="panel-glass rounded-full px-4 py-2 flex items-center gap-3 pointer-events-auto">
      <div class="flex items-center gap-2">
        <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]"></span>
        <span class="font-bold text-xs tracking-wider uppercase">Code Earth</span>
        <span class="text-slate-400 text-xs">/</span>
        <span class="text-xs font-mono opacity-80 truncate max-w-[130px]" title="{repo_name}">{repo_name}</span>
      </div>

      <div class="h-4 w-px bg-slate-300 dark:bg-slate-700"></div>

      <!-- Quick Metrics -->
      <div class="flex items-center gap-3 text-xs">
        <div class="flex items-center gap-1.5 cursor-pointer" onclick="filterByTier(0)" title="Filter direct changes">
          <span class="w-2 h-2 rounded-full bg-rose-500"></span>
          <span class="font-bold text-rose-500" id="stat-epicenter">0</span>
          <span class="text-[11px] opacity-70 hidden sm:inline">Epicenter</span>
        </div>
        <div class="flex items-center gap-1.5 cursor-pointer" onclick="filterByTier(1)" title="Filter direct ripple dependents">
          <span class="w-2 h-2 rounded-full bg-amber-500"></span>
          <span class="font-bold text-amber-500" id="stat-ripple">0</span>
          <span class="text-[11px] opacity-70 hidden sm:inline">Ripple</span>
        </div>
        <div class="flex items-center gap-1.5 cursor-pointer" onclick="filterByTier(2)" title="Safe bedrock files">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span class="font-bold text-emerald-500" id="stat-safe">0</span>
          <span class="text-[11px] opacity-70 hidden sm:inline">Safe</span>
        </div>
      </div>
    </div>

    <!-- Center: 4-MODE PERSPECTIVE SWITCHER -->
    <div class="panel-glass rounded-full p-1 flex items-center gap-1 pointer-events-auto shadow-md">
      <button id="viewBtnContinents" onclick="setViewMode('continents')" class="view-btn active px-3 py-1.5 rounded-full text-xs transition flex items-center gap-1.5" title="Topographic Continents View">
        <span>🗺️</span>
        <span class="hidden md:inline">Continents</span>
      </button>
      <button id="viewBtnGlobe" onclick="setViewMode('globe')" class="view-btn px-3 py-1.5 rounded-full text-xs transition flex items-center gap-1.5 opacity-80 hover:opacity-100" title="3D Orbital Planet View">
        <span>🌍</span>
        <span class="hidden md:inline">3D Globe</span>
      </button>
      <button id="viewBtnCity" onclick="setViewMode('city')" class="view-btn px-3 py-1.5 rounded-full text-xs transition flex items-center gap-1.5 opacity-80 hover:opacity-100" title="2.5D Isometric Code City View">
        <span>🏙️</span>
        <span class="hidden md:inline">Code City</span>
      </button>
      <button id="viewBtnGraph" onclick="setViewMode('graph')" class="view-btn px-3 py-1.5 rounded-full text-xs transition flex items-center gap-1.5 opacity-80 hover:opacity-100" title="Force-Directed Dependency Constellations">
        <span>🕸️</span>
        <span class="hidden md:inline">Neural Graph</span>
      </button>
    </div>

    <!-- Right: Command Shell, Explorer, Theme & Zoom Controls -->
    <div class="panel-glass rounded-full px-2.5 py-1.5 flex items-center gap-1.5 pointer-events-auto">
      
      <!-- Command Palette Trigger (Cmd+K) -->
      <button onclick="toggleCommandPalette()" class="px-2.5 py-1 rounded-full text-xs font-medium hover:bg-slate-200/50 dark:hover:bg-slate-800 transition flex items-center gap-1.5" title="Search Files (Ctrl+K or /)">
        <span>🔍</span>
        <span class="hidden lg:inline text-[11px]">Search</span>
        <kbd class="hidden sm:inline text-[9px] px-1 py-0.5 rounded bg-slate-200/60 dark:bg-slate-800 font-mono">/</kbd>
      </button>

      <!-- Left File Explorer Toggle -->
      <button id="btnToggleExplorer" onclick="toggleExplorer()" class="px-2.5 py-1 rounded-full text-xs font-medium hover:bg-slate-200/50 dark:hover:bg-slate-800 transition flex items-center gap-1" title="Toggle File Tree (B)">
        <span>📁</span>
        <span class="hidden lg:inline text-[11px]">Files</span>
      </button>

      <div class="h-4 w-px bg-slate-300 dark:bg-slate-700 mx-0.5"></div>

      <!-- Live Zoom Level Badge -->
      <span id="zoomPercent" class="font-mono text-[11px] font-bold min-w-[38px] text-center px-1" title="Current Zoom Scale">
        35%
      </span>

      <!-- Camera Zoom Actions -->
      <button onclick="zoomDelta(1.25)" class="w-7 h-7 flex items-center justify-center hover:bg-slate-200/50 dark:hover:bg-slate-800 rounded-full text-xs font-bold" title="Zoom In (+)">
        +
      </button>
      <button onclick="zoomDelta(0.8)" class="w-7 h-7 flex items-center justify-center hover:bg-slate-200/50 dark:hover:bg-slate-800 rounded-full text-xs font-bold" title="Zoom Out (-)">
        -
      </button>
      <button onclick="fitToScreen()" class="px-2 py-1 flex items-center gap-1 hover:bg-slate-200/50 dark:hover:bg-slate-800 rounded-full text-xs font-medium" title="Center & Fit View">
        <span>🎯</span>
        <span class="hidden md:inline text-[11px]">Center</span>
      </button>

      <div class="h-4 w-px bg-slate-300 dark:bg-slate-700 mx-0.5"></div>

      <!-- Light / Dark Theme Switcher -->
      <button id="themeToggleBtn" onclick="toggleTheme()" class="w-7 h-7 flex items-center justify-center hover:bg-slate-200/50 dark:hover:bg-slate-800 rounded-full text-xs transition" title="Toggle Light/Dark Theme">
        🌓
      </button>

      <!-- Fullscreen Toggle -->
      <button onclick="toggleFullScreen()" class="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 dark:bg-sky-500 dark:hover:bg-sky-400 text-white dark:text-slate-950 rounded-full text-xs font-medium transition" title="Fullscreen (F11)">
        ⛶
      </button>
    </div>
  </header>

  <!-- ======================================================== -->
  <!-- MAIN INTERACTIVE HARDWARE-ACCELERATED CANVAS             -->
  <!-- ======================================================== -->
  <canvas id="earthCanvas" class="w-full h-full"></canvas>

  <!-- ======================================================== -->
  <!-- LEFT COLLAPSIBLE FILE TREE EXPLORER (Linear / VS Code)   -->
  <!-- ======================================================== -->
  <aside id="explorerPanel" class="fixed top-16 left-3 bottom-14 w-72 panel-glass rounded-2xl p-3 shadow-2xl transition-all duration-300 -translate-x-[115%] pointer-events-auto z-20 flex flex-col gap-2">
    <div class="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
      <div class="flex items-center gap-2">
        <span class="font-bold text-xs uppercase tracking-wider">Repository Files</span>
        <span id="explorerCount" class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800">0</span>
      </div>
      <button onclick="toggleExplorer()" class="opacity-60 hover:opacity-100 text-sm p-1">✕</button>
    </div>

    <!-- Filter Search in Explorer -->
    <input id="explorerSearch" type="text" placeholder="Filter files..." 
           oninput="filterExplorerList(this.value)"
           class="w-full px-2.5 py-1.5 text-xs rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-sky-500">

    <!-- Scrollable Tree List -->
    <div id="explorerList" class="flex-1 overflow-y-auto space-y-1 pr-1 text-xs">
      <!-- Injected dynamically -->
    </div>
  </aside>

  <!-- ======================================================== -->
  <!-- RIGHT SLIDE-OUT DIFF & TELEMETRY INSPECTOR               -->
  <!-- ======================================================== -->
  <aside id="inspectorPanel" class="fixed top-16 right-3 bottom-14 w-96 panel-glass rounded-2xl p-4 shadow-2xl transition-all duration-300 translate-x-[115%] pointer-events-auto z-20 flex flex-col gap-3">
    <!-- Header -->
    <div class="flex items-start justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
      <div class="flex items-center gap-2.5">
        <div id="insBadge" class="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs text-white shadow-sm">
          PY
        </div>
        <div>
          <h2 id="insTitle" class="font-bold text-xs truncate max-w-[220px]" title="">file_name.py</h2>
          <p id="insDir" class="text-[10px] opacity-60 font-mono truncate max-w-[220px]">src/path</p>
        </div>
      </div>
      <button onclick="closeInspector()" class="opacity-60 hover:opacity-100 text-sm p-1">✕</button>
    </div>

    <!-- Status & Metrics Pills -->
    <div class="flex items-center gap-2">
      <span id="insTier" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400">
        ⚡ EPICENTER
      </span>
      <span id="insDiffStat" class="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
        +14 -2
      </span>
      <span id="insLoc" class="text-[10px] font-mono opacity-60">
        84 LOC
      </span>
    </div>

    <!-- Tabs: Unified Diff vs Dependency Map -->
    <div class="flex border-b border-slate-200 dark:border-slate-800 text-xs">
      <button id="insTabDiff" onclick="switchInspectorTab('diff')" class="px-3 py-1 font-semibold border-b-2 border-sky-500">
        Diff & Code
      </button>
      <button id="insTabDeps" onclick="switchInspectorTab('deps')" class="px-3 py-1 opacity-70 hover:opacity-100">
        Callers & Imports
      </button>
    </div>

    <!-- Content: Diff View -->
    <div id="insContentDiff" class="flex-1 overflow-y-auto pr-1 space-y-1 font-mono text-[10px]">
      <div id="insDiffLines" class="rounded-xl p-2 bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 min-h-[160px]">
        <!-- Unified diff lines injected dynamically -->
      </div>
    </div>

    <!-- Content: Callers & Dependencies -->
    <div id="insContentDeps" class="flex-1 overflow-y-auto pr-1 space-y-3 hidden text-xs">
      <div>
        <span class="text-[10px] uppercase font-bold tracking-wider opacity-60 block mb-1">Imported by (Callers):</span>
        <div id="insInboundList" class="space-y-1">
          <!-- Injected dynamically -->
        </div>
      </div>
      <div>
        <span class="text-[10px] uppercase font-bold tracking-wider opacity-60 block mb-1">Direct Imports:</span>
        <div id="insOutboundList" class="space-y-1">
          <!-- Injected dynamically -->
        </div>
      </div>
    </div>

    <!-- Quick Action Footer -->
    <div class="pt-2 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
      <button id="insFlyToBtn" class="px-3 py-1.5 rounded-full text-xs font-semibold bg-sky-500 hover:bg-sky-400 text-white transition flex items-center gap-1.5 shadow-sm">
        <span>🎯</span> <span>Focus Camera</span>
      </button>
      <span id="insFileTypeDesc" class="text-[10px] opacity-60">Python Module</span>
    </div>
  </aside>

  <!-- ======================================================== -->
  <!-- COMMAND PALETTE MODAL (Cmd+K / /)                        -->
  <!-- ======================================================== -->
  <div id="commandPalette" class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm hidden flex items-start justify-center pt-24 px-4 pointer-events-auto" onclick="onPaletteBackdrop(event)">
    <div class="panel-glass rounded-2xl max-w-lg w-full p-4 shadow-2xl flex flex-col gap-3 animate-in fade-in zoom-in-95 duration-150" onclick="event.stopPropagation()">
      <div class="flex items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
        <span class="text-slate-400">🔍</span>
        <input id="paletteInput" type="text" placeholder="Search files, extensions, blast tiers..." 
               class="flex-1 bg-transparent border-none text-sm focus:outline-none placeholder:text-slate-400"
               oninput="onPaletteSearch(this.value)" onkeydown="onPaletteKeyDown(event)">
        <kbd class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-500">ESC</kbd>
      </div>

      <!-- Quick Filter Chips -->
      <div class="flex flex-wrap items-center gap-1.5 text-[11px]">
        <button onclick="setPaletteFilter('all')" class="palette-chip px-2 py-0.5 rounded-full bg-slate-900 text-white dark:bg-sky-500 dark:text-slate-950 font-medium">All</button>
        <button onclick="setPaletteFilter('epicenter')" class="palette-chip px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">⚡ Epicenter</button>
        <button onclick="setPaletteFilter('ripple')" class="palette-chip px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">▲ Ripple</button>
        <button onclick="setPaletteFilter('py')" class="palette-chip px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">Python</button>
        <button onclick="setPaletteFilter('ts')" class="palette-chip px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">TypeScript</button>
      </div>

      <!-- Results list -->
      <div id="paletteResults" class="max-h-64 overflow-y-auto space-y-1 text-xs pr-1">
        <!-- Results injected dynamically -->
      </div>
    </div>
  </div>

  <!-- ======================================================== -->
  <!-- BOTTOM-LEFT RADAR / MINIMAP                              -->
  <!-- ======================================================== -->
  <div id="radarWidget" class="absolute bottom-3 left-3 z-20 panel-glass rounded-2xl p-2 shadow-lg pointer-events-auto flex flex-col gap-1 transition-opacity duration-200 hover:opacity-100 opacity-90">
    <div class="flex items-center justify-between px-1">
      <span class="text-[9px] font-bold uppercase tracking-wider opacity-60">Radar</span>
      <span class="text-[8px] opacity-40 font-mono">Click to Fly</span>
    </div>
    <canvas id="minimapCanvas" width="130" height="85" class="rounded-xl cursor-crosshair border border-slate-200 dark:border-slate-800 bg-[var(--radar-bg)]"></canvas>
  </div>

  <!-- ======================================================== -->
  <!-- OPTIONAL FLOATING FLIGHT HISTORY DRAWER                  -->
  <!-- ======================================================== -->
  <aside id="historyDrawer" class="fixed bottom-14 right-4 max-w-sm w-full panel-glass rounded-2xl p-4 shadow-2xl transition-all duration-300 translate-y-[200%] pointer-events-auto z-30">
    <div class="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
      <div class="flex items-center gap-2">
        <span class="text-xs font-bold uppercase tracking-wider">Flight Path Replay</span>
        <span id="stepCount" class="text-[11px] font-mono opacity-60">0 / 0</span>
      </div>
      <button onclick="toggleHistoryDrawer()" class="opacity-60 hover:opacity-100 text-sm p-1">✕</button>
    </div>
    
    <div class="py-3">
      <div class="flex items-center gap-2 mb-2">
        <span id="flightStep" class="px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 font-mono text-[10px] font-bold">Step 1</span>
        <span id="flightAction" class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 opacity-70 uppercase">IDLE</span>
      </div>
      <p id="flightThought" class="text-xs opacity-80 line-clamp-2">Replaying agent actions across repository...</p>
    </div>

    <div class="flex items-center gap-3 pt-1">
      <button id="btnPlay" onclick="togglePlay()" class="w-8 h-8 rounded-full bg-slate-900 text-white dark:bg-sky-500 dark:text-slate-950 flex items-center justify-center font-bold text-xs transition">
        ▶
      </button>
      <input id="timeline" type="range" min="0" max="1" value="0" step="1" 
             class="flex-1 h-1 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-sky-500 focus:outline-none">
      <button onclick="stepDelta(-1)" class="p-1 opacity-60 hover:opacity-100 text-xs">◀</button>
      <button onclick="stepDelta(1)" class="p-1 opacity-60 hover:opacity-100 text-xs">▶</button>
    </div>
  </aside>

  <!-- Bottom Trigger Pill for Flight History -->
  <footer class="absolute bottom-3 right-4 z-20 pointer-events-none">
    <button onclick="toggleHistoryDrawer()" class="panel-glass rounded-full px-3.5 py-1.5 text-xs font-medium hover:bg-white dark:hover:bg-slate-800 transition flex items-center gap-1.5 pointer-events-auto shadow-md">
      <span>⏱️</span>
      <span>Flight History</span>
    </button>
  </footer>

  <!-- ======================================================== -->
  <!-- MULTI-PERSPECTIVE CANVAS SCRIPT ENGINE                   -->
  <!-- ======================================================== -->
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

    // View Mode State
    let currentViewMode = "continents"; // continents | globe | city | graph

    // Camera & Coordinates State
    let scale = 0.35;
    let panX = width / 2;
    let panY = height / 2;
    let isDragging = false;
    let startX = 0, startY = 0;
    let hoveredNode = null;
    let activeNode = null;

    // 3D Globe Rotation State
    let globeRotX = 0.25;
    let globeRotY = 0.0;
    let globeLastMouseX = 0;
    let globeLastMouseY = 0;

    // Force Graph Coordinates State
    const graphCoords = new Map();
    const cityCoords = new Map();
    const globeCoords = new Map();
    const continentCoords = new Map();
    const screenNodeMap = new Map();

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

    // ==========================================
    // PRECOMPUTE COORDINATES ACROSS ALL 4 MODES
    // ==========================================
    const moduleList = Object.keys(DATA.modules);
    const continentLayout = new Map();
    const cols = Math.ceil(Math.sqrt(moduleList.length || 1));
    const continentSpacingX = 900;
    const continentSpacingY = 750;

    let worldMinX = Infinity, worldMaxX = -Infinity, worldMinY = Infinity, worldMaxY = -Infinity;

    // 1. Continents & City Coordinates
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

      // Continents node positions
      files.forEach((fpath, fi) => {{
        const angle = (fi / files.length) * Math.PI * 2 + (mi * 0.4);
        const dist = Math.min(baseRadius - 60, (fi + 1) * 50);
        continentCoords.set(fpath, {{
          x: cx + Math.cos(angle) * dist,
          y: cy + Math.sin(angle) * dist
        }});

        // City grid positions
        const cityCol = fi % 4;
        const cityRow = Math.floor(fi / 4);
        cityCoords.set(fpath, {{
          x: cx - 120 + cityCol * 80,
          y: cy - 120 + cityRow * 80,
          loc: DATA.nodes.find(n => n.id === fpath)?.loc || 30
        }});
      }});
    }});

    // 2. 3D Globe Spherical Coordinates (lat/lon)
    DATA.nodes.forEach((node, idx) => {{
      const phi = Math.acos(-1 + (2 * idx) / Math.max(1, DATA.nodes.length));
      const theta = Math.sqrt(DATA.nodes.length * Math.PI) * phi;
      globeCoords.set(node.id, {{
        lat: phi - Math.PI / 2,
        lon: theta
      }});
    }});

    // 3. Neural Force-Directed Graph Layout Simulation
    DATA.nodes.forEach((node, idx) => {{
      const angle = (idx / DATA.nodes.length) * Math.PI * 2;
      const radius = 250 + (idx % 3) * 120;
      graphCoords.set(node.id, {{
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        vx: 0, vy: 0
      }});
    }});

    // Pre-relax force layout
    for (let iter = 0; iter < 90; iter++) {{
      // Repulsion
      DATA.nodes.forEach(n1 => {{
        const p1 = graphCoords.get(n1.id);
        DATA.nodes.forEach(n2 => {{
          if (n1.id === n2.id) return;
          const p2 = graphCoords.get(n2.id);
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.max(15, Math.hypot(dx, dy));
          if (dist < 380) {{
            const force = (1200 / (dist * dist));
            p1.vx += (dx / dist) * force;
            p1.vy += (dy / dist) * force;
          }}
        }});
      }});

      // Link attraction
      DATA.links.forEach(link => {{
        const p1 = graphCoords.get(link.source);
        const p2 = graphCoords.get(link.target);
        if (p1 && p2) {{
          const dx = p2.x - p1.x;
          const dy = p2.y - p1.y;
          const dist = Math.max(1, Math.hypot(dx, dy));
          const force = (dist - 140) * 0.05;
          p1.vx += (dx / dist) * force;
          p1.vy += (dy / dist) * force;
          p2.vx -= (dx / dist) * force;
          p2.vy -= (dy / dist) * force;
        }}
      }});

      // Gravity & Damping
      DATA.nodes.forEach(n => {{
        const p = graphCoords.get(n.id);
        p.vx -= p.x * 0.015;
        p.vy -= p.y * 0.015;
        p.x += p.vx * 0.7;
        p.y += p.vy * 0.7;
        p.vx *= 0.85;
        p.vy *= 0.85;
      }});
    }}

    if (worldMinX === Infinity) {{
      worldMinX = -400; worldMaxX = 400; worldMinY = -300; worldMaxY = 300;
    }}

    let animTime = 0;

    // ==========================================
    // VIEW SWITCHER DISPATCHER
    // ==========================================
    function setViewMode(mode) {{
      currentViewMode = mode;
      document.querySelectorAll(".view-btn").forEach(b => b.classList.remove("active"));
      if (mode === "continents") document.getElementById("viewBtnContinents")?.classList.add("active");
      if (mode === "globe") document.getElementById("viewBtnGlobe")?.classList.add("active");
      if (mode === "city") document.getElementById("viewBtnCity")?.classList.add("active");
      if (mode === "graph") document.getElementById("viewBtnGraph")?.classList.add("active");

      if (mode === "globe") {{
        scale = 1.0;
        panX = width / 2;
        panY = height / 2;
      }} else if (mode === "city") {{
        scale = 0.75;
      }} else if (mode === "graph") {{
        scale = 0.85;
      }}
      clampCamera();
      updateZoomUI();
    }}

    // CAMERA CLAMPING
    function clampCamera() {{
      if (currentViewMode === "globe") return; // Globe stays centered
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

    function updateZoomUI() {{
      const zPill = document.getElementById("zoomPercent");
      if (zPill) zPill.textContent = Math.round(scale * 100) + "%";
    }}

    function fitToScreen() {{
      if (currentViewMode === "globe") {{
        panX = width / 2;
        panY = height / 2;
        globeRotX = 0.25;
        globeRotY = 0.0;
        scale = 1.0;
        updateZoomUI();
        return;
      }}
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

      clampCamera();
      updateZoomUI();
    }}

    // ==========================================
    // MOUSE & TOUCH EVENT LISTENERS
    // ==========================================
    canvas.addEventListener("wheel", (e) => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      const mouseX = e.clientX;
      const mouseY = e.clientY;

      if (currentViewMode === "globe") {{
        scale = Math.min(Math.max(scale * zoomFactor, 0.4), 2.8);
      }} else {{
        const worldX = (mouseX - panX) / scale;
        const worldY = (mouseY - panY) / scale;
        scale = Math.min(Math.max(scale * zoomFactor, 0.12), 6.0);
        panX = mouseX - worldX * scale;
        panY = mouseY - worldY * scale;
        clampCamera();
      }}
      updateZoomUI();
    }});

    canvas.addEventListener("mousedown", (e) => {{
      isDragging = true;
      startX = e.clientX - panX;
      startY = e.clientY - panY;
      globeLastMouseX = e.clientX;
      globeLastMouseY = e.clientY;
    }});

    window.addEventListener("mousemove", (e) => {{
      if (isDragging) {{
        if (currentViewMode === "globe") {{
          const dx = e.clientX - globeLastMouseX;
          const dy = e.clientY - globeLastMouseY;
          globeRotY += dx * 0.007;
          globeRotX = Math.max(-Math.PI / 2.2, Math.min(Math.PI / 2.2, globeRotX + dy * 0.007));
          globeLastMouseX = e.clientX;
          globeLastMouseY = e.clientY;
        }} else {{
          panX = e.clientX - startX;
          panY = e.clientY - startY;
          clampCamera();
        }}
      }} else {{
        // Screen-space hit testing across all modes
        let found = null;
        for (const [nid, sc] of screenNodeMap.entries()) {{
          if (!sc.visible) continue;
          const d = Math.hypot(e.clientX - sc.x, e.clientY - sc.y);
          if (d <= sc.radius) {{
            found = DATA.nodes.find(n => n.id === nid);
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
        selectNode(hoveredNode);
      }}
    }});

    canvas.addEventListener("dblclick", () => {{
      if (hoveredNode) {{
        flyToNode(hoveredNode.id);
      }} else {{
        fitToScreen();
      }}
    }});

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

    // ==========================================
    // THEME SWITCHER (Light ↔ Obsidian Dark)
    // ==========================================
    let isDarkTheme = localStorage.getItem("code_earth_theme") === "dark";
    if (isDarkTheme) document.body.classList.add("theme-dark");

    function toggleTheme() {{
      isDarkTheme = !isDarkTheme;
      if (isDarkTheme) {{
        document.body.classList.add("theme-dark");
        localStorage.setItem("code_earth_theme", "dark");
      }} else {{
        document.body.classList.remove("theme-dark");
        localStorage.setItem("code_earth_theme", "light");
      }}
    }}

    // ==========================================
    // INSPECTOR DRAWER CONTROLLER
    // ==========================================
    function selectNode(node) {{
      activeNode = node;
      const panel = document.getElementById("inspectorPanel");
      if (!panel || !node) return;

      const ftype = getFileType(node.name || node.id);
      document.getElementById("insTitle").textContent = node.name;
      document.getElementById("insTitle").title = node.id;
      document.getElementById("insDir").textContent = node.dir;
      document.getElementById("insFileTypeDesc").textContent = ftype.name;

      const badge = document.getElementById("insBadge");
      badge.textContent = ftype.label;
      badge.style.backgroundColor = ftype.bg;
      badge.style.color = ftype.color;

      const tierPill = document.getElementById("insTier");
      if (node.tier === 0) {{
        tierPill.textContent = "⚡ EPICENTER (ACTIVE EDIT)";
        tierPill.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400";
      }} else if (node.tier === 1) {{
        tierPill.textContent = "▲ RIPPLE ZONE";
        tierPill.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400";
      }} else {{
        tierPill.textContent = "✓ SAFE BEDROCK";
        tierPill.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400";
      }}

      document.getElementById("insDiffStat").textContent = `+${{node.added}} -${{node.deleted}}`;
      document.getElementById("insLoc").textContent = `${{node.loc}} LOC`;
      document.getElementById("insFlyToBtn").onclick = () => flyToNode(node.id);

      // Populate Diff
      const diffContainer = document.getElementById("insDiffLines");
      diffContainer.innerHTML = "";
      const lines = (node.diffLines && node.diffLines.length) ? node.diffLines : (node.codeLines || []).slice(0, 30);
      if (!lines.length) {{
        diffContainer.innerHTML = "<p class='opacity-50 text-[11px] p-2'>No active diffs. Clean working tree.</p>";
      }} else {{
        lines.forEach(l => {{
          const row = document.createElement("div");
          row.className = "px-1.5 py-0.5 rounded flex items-start gap-2 text-[10px]";
          if (l.type === "add") {{
            row.style.backgroundColor = "var(--diff-add-bg)";
            row.style.color = "var(--diff-add-text)";
            row.innerHTML = `<span class='font-bold'>+</span><span class='break-all'>${{escapeHtml(l.text)}}</span>`;
          }} else if (l.type === "del") {{
            row.style.backgroundColor = "var(--diff-del-bg)";
            row.style.color = "var(--diff-del-text)";
            row.innerHTML = `<span class='font-bold'>-</span><span class='break-all'>${{escapeHtml(l.text)}}</span>`;
          }} else {{
            row.innerHTML = `<span class='opacity-40'> </span><span class='opacity-70 break-all'>${{escapeHtml(l.text !== undefined ? l.text : l)}}</span>`;
          }}
          diffContainer.appendChild(row);
        }});
      }}

      // Populate Inbound Callers & Outbound Imports
      const inList = document.getElementById("insInboundList");
      const outList = document.getElementById("insOutboundList");
      inList.innerHTML = "";
      outList.innerHTML = "";

      if (node.inbound && node.inbound.length) {{
        node.inbound.forEach(depId => {{
          const btn = document.createElement("button");
          btn.className = "w-full text-left px-2 py-1 rounded bg-slate-100 dark:bg-slate-800/60 hover:bg-sky-50 dark:hover:bg-sky-950/40 text-[11px] truncate flex items-center justify-between";
          btn.innerHTML = `<span>${{depId.split('/').pop()}}</span><span class='text-[9px] opacity-40'>fly ➔</span>`;
          btn.onclick = () => flyToNode(depId);
          inList.appendChild(btn);
        }});
      }} else {{
        inList.innerHTML = "<p class='opacity-40 text-[10px]'>No incoming callers.</p>";
      }}

      if (node.outbound && node.outbound.length) {{
        node.outbound.forEach(depId => {{
          const btn = document.createElement("button");
          btn.className = "w-full text-left px-2 py-1 rounded bg-slate-100 dark:bg-slate-800/60 hover:bg-sky-50 dark:hover:bg-sky-950/40 text-[11px] truncate flex items-center justify-between";
          btn.innerHTML = `<span>${{depId.split('/').pop()}}</span><span class='text-[9px] opacity-40'>fly ➔</span>`;
          btn.onclick = () => flyToNode(depId);
          outList.appendChild(btn);
        }});
      }} else {{
        outList.innerHTML = "<p class='opacity-40 text-[10px]'>No outgoing imports.</p>";
      }}

      panel.classList.remove("translate-x-[115%]");
    }}

    function closeInspector() {{
      const panel = document.getElementById("inspectorPanel");
      if (panel) panel.classList.add("translate-x-[115%]");
      activeNode = null;
    }}

    function switchInspectorTab(tab) {{
      const tDiff = document.getElementById("insTabDiff");
      const tDeps = document.getElementById("insTabDeps");
      const cDiff = document.getElementById("insContentDiff");
      const cDeps = document.getElementById("insContentDeps");
      if (tab === "diff") {{
        tDiff.className = "px-3 py-1 font-semibold border-b-2 border-sky-500";
        tDeps.className = "px-3 py-1 opacity-70 hover:opacity-100";
        cDiff.classList.remove("hidden");
        cDeps.classList.add("hidden");
      }} else {{
        tDeps.className = "px-3 py-1 font-semibold border-b-2 border-sky-500";
        tDiff.className = "px-3 py-1 opacity-70 hover:opacity-100";
        cDeps.classList.remove("hidden");
        cDiff.classList.add("hidden");
      }}
    }}

    function escapeHtml(str) {{
      return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }}

    // ==========================================
    // LEFT FILE EXPLORER CONTROLLER
    // ==========================================
    let explorerOpen = false;
    function toggleExplorer() {{
      explorerOpen = !explorerOpen;
      const el = document.getElementById("explorerPanel");
      if (explorerOpen) {{
        el.classList.remove("-translate-x-[115%]");
        renderExplorerList("");
      }} else {{
        el.classList.add("-translate-x-[115%]");
      }}
    }}

    function renderExplorerList(filterQuery) {{
      const listEl = document.getElementById("explorerList");
      const countEl = document.getElementById("explorerCount");
      if (!listEl) return;
      listEl.innerHTML = "";

      const q = filterQuery.toLowerCase();
      const filtered = DATA.nodes.filter(n => n.id.toLowerCase().includes(q) || n.name.toLowerCase().includes(q));
      if (countEl) countEl.textContent = filtered.length;

      filtered.forEach(node => {{
        const row = document.createElement("div");
        row.className = "p-1.5 rounded-xl hover:bg-slate-200/50 dark:hover:bg-slate-800/60 cursor-pointer flex items-center justify-between transition";
        const ftype = getFileType(node.name || node.id);
        
        let pipColor = "#10b981";
        if (node.tier === 0) pipColor = "#f43f5e";
        else if (node.tier === 1) pipColor = "#f59e0b";

        row.innerHTML = `
          <div class="flex items-center gap-2 truncate">
            <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" style="background-color: ${{pipColor}}"></span>
            <span class="text-[9px] font-bold px-1 rounded flex-shrink-0" style="background:${{ftype.bg}}; color:${{ftype.color}}">${{ftype.label}}</span>
            <span class="truncate font-medium text-[11px]">${{node.name}}</span>
          </div>
          <span class="text-[9px] font-mono opacity-50 flex-shrink-0">${{node.added ? `+${{node.added}}` : ""}}</span>
        `;
        row.onclick = () => {{
          selectNode(node);
          flyToNode(node.id);
        }};
        listEl.appendChild(row);
      }});
    }}

    function filterExplorerList(val) {{
      renderExplorerList(val);
    }}

    // ==========================================
    // COMMAND PALETTE CONTROLLER (Cmd+K)
    // ==========================================
    let paletteActiveFilter = "all";
    function toggleCommandPalette() {{
      const p = document.getElementById("commandPalette");
      if (!p) return;
      const isHidden = p.classList.contains("hidden");
      if (isHidden) {{
        p.classList.remove("hidden");
        const inp = document.getElementById("paletteInput");
        inp.value = "";
        inp.focus();
        renderPaletteResults("");
      }} else {{
        p.classList.add("hidden");
      }}
    }}

    function onPaletteBackdrop(e) {{
      toggleCommandPalette();
    }}

    function setPaletteFilter(filter) {{
      paletteActiveFilter = filter;
      document.querySelectorAll(".palette-chip").forEach(c => {{
        c.className = "palette-chip px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300";
      }});
      event.target.className = "palette-chip px-2 py-0.5 rounded-full bg-slate-900 text-white dark:bg-sky-500 dark:text-slate-950 font-medium";
      renderPaletteResults(document.getElementById("paletteInput").value);
    }}

    function onPaletteSearch(val) {{
      renderPaletteResults(val);
    }}

    function renderPaletteResults(query) {{
      const container = document.getElementById("paletteResults");
      if (!container) return;
      container.innerHTML = "";
      const q = (query || "").toLowerCase();

      let list = DATA.nodes.filter(n => n.id.toLowerCase().includes(q) || n.name.toLowerCase().includes(q));
      if (paletteActiveFilter === "epicenter") list = list.filter(n => n.tier === 0);
      else if (paletteActiveFilter === "ripple") list = list.filter(n => n.tier === 1);
      else if (paletteActiveFilter === "py") list = list.filter(n => n.name.endsWith(".py"));
      else if (paletteActiveFilter === "ts") list = list.filter(n => n.name.endsWith(".ts") || n.name.endsWith(".tsx"));

      if (!list.length) {{
        container.innerHTML = "<p class='p-3 text-center opacity-50 text-xs'>No matching files found.</p>";
        return;
      }}

      list.slice(0, 15).forEach((node, idx) => {{
        const item = document.createElement("div");
        item.className = "p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer flex items-center justify-between";
        const ftype = getFileType(node.name || node.id);

        let tierLabel = "Safe";
        let tierColor = "#10b981";
        if (node.tier === 0) {{ tierLabel = "Epicenter"; tierColor = "#f43f5e"; }}
        else if (node.tier === 1) {{ tierLabel = "Ripple"; tierColor = "#f59e0b"; }}

        item.innerHTML = `
          <div class="flex items-center gap-2 truncate">
            <span class="text-[9px] font-bold px-1.5 py-0.5 rounded" style="background:${{ftype.bg}}; color:${{ftype.color}}">${{ftype.label}}</span>
            <div>
              <p class="font-semibold text-xs truncate">${{node.name}}</p>
              <p class="text-[10px] opacity-50 font-mono truncate">${{node.dir}}</p>
            </div>
          </div>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full" style="color:${{tierColor}}; background:${{tierColor}}18">${{tierLabel}}</span>
        `;
        item.onclick = () => {{
          toggleCommandPalette();
          selectNode(node);
          flyToNode(node.id);
        }};
        container.appendChild(item);
      }});
    }}

    function onPaletteKeyDown(e) {{
      if (e.key === "Escape") toggleCommandPalette();
    }}

    // Global Keybindings (/ and Cmd+K and B)
    window.addEventListener("keydown", (e) => {{
      if ((e.key === "/" || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k")) && e.target.tagName !== "INPUT") {{
        e.preventDefault();
        toggleCommandPalette();
      }}
      if (e.key.toLowerCase() === "b" && e.target.tagName !== "INPUT") {{
        e.preventDefault();
        toggleExplorer();
      }}
    }});

    // Filter by Topbar Metric Pills
    function filterByTier(tier) {{
      toggleCommandPalette();
      if (tier === 0) setPaletteFilter("epicenter");
      else if (tier === 1) setPaletteFilter("ripple");
      else setPaletteFilter("all");
    }}

    // Smooth Fly-To Camera Navigation
    function flyToNode(nodeId) {{
      const n = DATA.nodes.find(node => node.id === nodeId);
      if (!n) return;
      selectNode(n);

      if (currentViewMode === "globe") {{
        const gc = globeCoords.get(nodeId);
        if (gc) {{
          globeRotY = -gc.lon;
          globeRotX = -gc.lat;
          scale = 1.35;
        }}
      }} else if (currentViewMode === "continents") {{
        const pt = continentCoords.get(nodeId);
        if (pt) {{
          scale = 2.4;
          panX = width / 2 - pt.x * scale;
          panY = height / 2 - pt.y * scale;
          clampCamera();
        }}
      }} else if (currentViewMode === "city") {{
        const pt = cityCoords.get(nodeId);
        if (pt) {{
          const isoX = (pt.x - pt.y) * 0.866;
          const isoY = (pt.x + pt.y) * 0.5;
          scale = 1.5;
          panX = width / 2 - isoX * scale;
          panY = height / 2 - isoY * scale;
          clampCamera();
        }}
      }} else if (currentViewMode === "graph") {{
        const pt = graphCoords.get(nodeId);
        if (pt) {{
          scale = 1.8;
          panX = width / 2 - pt.x * scale;
          panY = height / 2 - pt.y * scale;
          clampCamera();
        }}
      }}
      updateZoomUI();
    }}

    // ==========================================
    // RADAR / MINIMAP NAVIGATION
    // ==========================================
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

      // Draw mini continents
      continentLayout.forEach((cont) => {{
        const mx = toMmX(cont.cx);
        const my = toMmY(cont.cy);
        const mr = (cont.baseRadius / wSpan) * mmW;

        mmCtx.beginPath();
        mmCtx.arc(mx, my, Math.max(3, mr), 0, Math.PI * 2);
        mmCtx.fillStyle = cont.hasEpicenter ? "#fecdd3" : (isDarkTheme ? "#334155" : "#e2e8f0");
        mmCtx.fill();
      }});

      // Viewport rectangle
      if (currentViewMode !== "globe") {{
        const leftW = (0 - panX) / scale;
        const rightW = (width - panX) / scale;
        const topW = (0 - panY) / scale;
        const bottomW = (height - panY) / scale;

        const vx = toMmX(leftW);
        const vy = toMmY(topW);
        const vw = toMmX(rightW) - vx;
        const vh = toMmY(bottomW) - vy;

        mmCtx.strokeStyle = isDarkTheme ? "#38bdf8" : "#0f172a";
        mmCtx.lineWidth = 1.5;
        mmCtx.strokeRect(vx, vy, vw, vh);
      }}
    }}

    // ==========================================
    // MAIN MULTI-VIEW RENDERING LOOP
    // ==========================================
    function draw() {{
      animTime += 0.025;
      screenNodeMap.clear();
      ctx.clearRect(0, 0, width, height);

      // Canvas background
      ctx.fillStyle = isDarkTheme ? "#090d16" : "#f8fafc";
      ctx.fillRect(0, 0, width, height);

      if (currentViewMode === "continents") {{
        renderContinentsMode();
      }} else if (currentViewMode === "globe") {{
        renderGlobeMode();
      }} else if (currentViewMode === "city") {{
        renderCityMode();
      }} else if (currentViewMode === "graph") {{
        renderGraphMode();
      }}

      renderRadar();
      requestAnimationFrame(draw);
    }}

    // ----------------------------------------------------
    // MODE 1: TOPOGRAPHIC CONTINENTS (Organic Landscape)
    // ----------------------------------------------------
    function renderContinentsMode() {{
      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(scale, scale);

      // 1. Draw Landmasses
      continentLayout.forEach((cont, modName) => {{
        const pts = cont.points;
        if (!pts.length) return;

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
        ctx.fillStyle = isDarkTheme ? "#131b2e" : "#ffffff";
        ctx.shadowColor = isDarkTheme ? "rgba(0,0,0,0.4)" : "rgba(15, 23, 42, 0.06)";
        ctx.shadowBlur = 24;
        ctx.fill();
        ctx.shadowBlur = 0;

        ctx.strokeStyle = cont.hasEpicenter ? "#f43f5e" : (isDarkTheme ? "#1e293b" : "#cbd5e1");
        ctx.lineWidth = 1.6 / scale;
        ctx.stroke();

        if (scale < 1.4) {{
          ctx.fillStyle = cont.hasEpicenter ? "#f43f5e" : (isDarkTheme ? "#94a3b8" : "#475569");
          ctx.font = `bold ${{Math.max(12, 18)}}px -apple-system, sans-serif`;
          ctx.textAlign = "center";
          ctx.fillText(`⯎ ${{modName.toUpperCase()}}`, cont.cx, cont.cy - cont.baseRadius - 14);
        }}
      }});

      // 2. Draw Dependency Edges
      DATA.links.forEach(l => {{
        const src = continentCoords.get(l.source);
        const tgt = continentCoords.get(l.target);
        if (!src || !tgt) return;

        ctx.strokeStyle = isDarkTheme ? "rgba(56, 189, 248, 0.3)" : "rgba(203, 213, 225, 0.75)";
        ctx.lineWidth = Math.max(1, 1.4 / scale);
        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);
        ctx.stroke();
      }});

      // 3. Draw Nodes with File Extension Badges
      DATA.nodes.forEach(node => {{
        const pt = continentCoords.get(node.id);
        if (!pt) return;

        // Record screen position for hit testing
        const screenX = panX + pt.x * scale;
        const screenY = panY + pt.y * scale;
        const radius = (scale < 0.55 ? 24 : 32) * (hoveredNode?.id === node.id ? 1.2 : 1.0);
        screenNodeMap.set(node.id, {{ x: screenX, y: screenY, radius: radius * scale, visible: true }});

        renderFileBadgeNode(node, pt.x, pt.y, scale);
      }});

      ctx.restore();
    }}

    // ----------------------------------------------------
    // MODE 2: 3D ORBITAL GLOBE (Interactive Sphere)
    // ----------------------------------------------------
    function renderGlobeMode() {{
      const cx = width / 2;
      const cy = height / 2;
      const R = Math.min(width, height) * 0.35 * scale;

      // Atmospheric Rim Glow
      const atmGrad = ctx.createRadialGradient(cx, cy, R * 0.85, cx, cy, R * 1.25);
      atmGrad.addColorStop(0, isDarkTheme ? "rgba(56, 189, 248, 0.25)" : "rgba(14, 165, 233, 0.15)");
      atmGrad.addColorStop(1, "rgba(56, 189, 248, 0)");
      ctx.fillStyle = atmGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.25, 0, Math.PI * 2);
      ctx.fill();

      // Planet Sphere Body
      ctx.fillStyle = isDarkTheme ? "#0b1220" : "#f1f5f9";
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = isDarkTheme ? "#38bdf8" : "#94a3b8";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Latitude Circles & Longitude Ellipses
      ctx.strokeStyle = isDarkTheme ? "rgba(56, 189, 248, 0.15)" : "rgba(148, 163, 184, 0.3)";
      ctx.lineWidth = 1;
      [-0.6, -0.3, 0, 0.3, 0.6].forEach(latFrac => {{
        const rLat = R * Math.cos(latFrac * Math.PI / 2);
        const yLat = cy + R * Math.sin(latFrac * Math.PI / 2) * Math.cos(globeRotX);
        ctx.beginPath();
        ctx.ellipse(cx, yLat, rLat, rLat * Math.abs(Math.sin(globeRotX)), 0, 0, Math.PI * 2);
        ctx.stroke();
      }});

      // 3D Projected Coordinates for each node
      const projectedNodes = [];
      DATA.nodes.forEach(node => {{
        const gc = globeCoords.get(node.id);
        if (!gc) return;

        const x0 = R * Math.cos(gc.lat) * Math.sin(gc.lon);
        const y0 = -R * Math.sin(gc.lat);
        const z0 = R * Math.cos(gc.lat) * Math.cos(gc.lon);

        // Rotate Y (Yaw)
        const x1 = x0 * Math.cos(globeRotY) + z0 * Math.sin(globeRotY);
        const z1 = -x0 * Math.sin(globeRotY) + z0 * Math.cos(globeRotY);

        // Rotate X (Pitch)
        const y2 = y0 * Math.cos(globeRotX) - z1 * Math.sin(globeRotX);
        const z2 = y0 * Math.sin(globeRotX) + z1 * Math.cos(globeRotX);

        projectedNodes.push({{
          node,
          x: cx + x1,
          y: cy + y2,
          z: z2,
          visible: z2 > -R * 0.1
        }});
      }});

      // Depth sort
      projectedNodes.sort((a, b) => a.z - b.z);

      // Draw Edges on Globe
      DATA.links.forEach(l => {{
        const p1 = projectedNodes.find(pn => pn.node.id === l.source);
        const p2 = projectedNodes.find(pn => pn.node.id === l.target);
        if (p1 && p2 && p1.visible && p2.visible) {{
          ctx.strokeStyle = isDarkTheme ? "rgba(56, 189, 248, 0.4)" : "rgba(2, 132, 199, 0.4)";
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }}
      }});

      // Draw Nodes on Globe
      projectedNodes.forEach(pn => {{
        if (!pn.visible) return;
        const opacity = pn.z > 0 ? 1.0 : Math.max(0.2, (pn.z + R * 0.1) / (R * 0.1));
        ctx.globalAlpha = opacity;

        const isHovered = hoveredNode && hoveredNode.id === pn.node.id;
        const isActive = activeNode && activeNode.id === pn.node.id;
        const ftype = getFileType(pn.node.name || pn.node.id);
        const size = (isHovered || isActive ? 34 : 26);
        const half = size / 2;

        screenNodeMap.set(pn.node.id, {{ x: pn.x, y: pn.y, radius: half + 4, visible: pn.z > 0 }});

        ctx.save();
        ctx.translate(pn.x, pn.y);

        // Badge Background
        ctx.fillStyle = ftype.bg;
        ctx.beginPath();
        ctx.roundRect(-half, -half, size, size, 6);
        ctx.fill();

        // Icon Glyph
        ctx.fillStyle = ftype.color;
        ctx.font = `bold ${{Math.round(size * 0.42)}}px -apple-system, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(ftype.label, 0, 0);

        // Tier Border
        ctx.strokeStyle = pn.node.tier === 0 ? "#f43f5e" : (pn.node.tier === 1 ? "#f59e0b" : "#ffffff");
        ctx.lineWidth = pn.node.tier === 0 ? 2.2 : 1.2;
        ctx.stroke();

        ctx.restore();
        ctx.globalAlpha = 1.0;
      }});
    }}

    // ----------------------------------------------------
    // MODE 3: 2.5D ISOMETRIC CODE CITY (Skyscrapers)
    // ----------------------------------------------------
    function renderCityMode() {{
      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(scale, scale);

      // Depth sort buildings from back to front
      const sortedCityNodes = [...DATA.nodes].sort((a, b) => {{
        const pa = cityCoords.get(a.id) || {{ x: 0, y: 0 }};
        const pb = cityCoords.get(b.id) || {{ x: 0, y: 0 }};
        return (pa.x + pa.y) - (pb.x + pb.y);
      }});

      // Draw Skyway Cables
      DATA.links.forEach(l => {{
        const pa = cityCoords.get(l.source);
        const pb = cityCoords.get(l.target);
        if (!pa || !pb) return;

        const isoA_X = (pa.x - pa.y) * 0.866;
        const isoA_Y = (pa.x + pa.y) * 0.5 - (30 + Math.min(pa.loc, 250) * 0.4);
        const isoB_X = (pb.x - pb.y) * 0.866;
        const isoB_Y = (pb.x + pb.y) * 0.5 - (30 + Math.min(pb.loc, 250) * 0.4);

        ctx.strokeStyle = isDarkTheme ? "rgba(56, 189, 248, 0.4)" : "rgba(14, 165, 233, 0.4)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(isoA_X, isoA_Y);
        const midX = (isoA_X + isoB_X) / 2;
        const midY = Math.min(isoA_Y, isoB_Y) - 40;
        ctx.quadraticCurveTo(midX, midY, isoB_X, isoB_Y);
        ctx.stroke();
      }});

      // Draw 3D Isometric Buildings
      sortedCityNodes.forEach(node => {{
        const pt = cityCoords.get(node.id);
        if (!pt) return;

        const isoX = (pt.x - pt.y) * 0.866;
        const isoY = (pt.x + pt.y) * 0.5;
        const H = 35 + Math.min(pt.loc, 250) * 0.45;
        const W = 32;

        const isHovered = hoveredNode && hoveredNode.id === node.id;
        const isActive = activeNode && activeNode.id === node.id;
        const ftype = getFileType(node.name || node.id);

        const screenX = panX + isoX * scale;
        const screenY = panY + (isoY - H) * scale;
        screenNodeMap.set(node.id, {{ x: screenX, y: screenY, radius: 24 * scale, visible: true }});

        ctx.save();
        ctx.translate(isoX, isoY);

        // Left Facade
        ctx.fillStyle = node.tier === 0 ? "#be123c" : (node.tier === 1 ? "#d97706" : (isDarkTheme ? "#1e293b" : "#94a3b8"));
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(-W * 0.866, W * 0.5);
        ctx.lineTo(-W * 0.866, W * 0.5 - H);
        ctx.lineTo(0, -H);
        ctx.closePath();
        ctx.fill();

        // Right Facade (Darker shadow)
        ctx.fillStyle = node.tier === 0 ? "#9f1239" : (node.tier === 1 ? "#b45309" : (isDarkTheme ? "#0f172a" : "#64748b"));
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(W * 0.866, W * 0.5);
        ctx.lineTo(W * 0.866, W * 0.5 - H);
        ctx.lineTo(0, -H);
        ctx.closePath();
        ctx.fill();

        // Rooftop Diamond (Lightest)
        ctx.fillStyle = ftype.bg;
        ctx.beginPath();
        ctx.moveTo(0, -H - W * 0.5);
        ctx.lineTo(-W * 0.866, -H);
        ctx.lineTo(0, -H + W * 0.5);
        ctx.lineTo(W * 0.866, -H);
        ctx.closePath();
        ctx.fill();

        ctx.strokeStyle = isHovered || isActive ? "#38bdf8" : (node.tier === 0 ? "#f43f5e" : "#ffffff");
        ctx.lineWidth = isHovered || isActive ? 2.5 : 1;
        ctx.stroke();

        // Rooftop Emblem
        ctx.fillStyle = ftype.color;
        ctx.font = "bold 11px -apple-system, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(ftype.label, 0, -H);

        // Antenna on Epicenter buildings
        if (node.tier === 0) {{
          ctx.strokeStyle = "#f43f5e";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(0, -H - W * 0.5);
          ctx.lineTo(0, -H - W * 0.5 - 20);
          ctx.stroke();

          ctx.fillStyle = "#f43f5e";
          ctx.beginPath();
          ctx.arc(0, -H - W * 0.5 - 20, 3, 0, Math.PI * 2);
          ctx.fill();
        }}

        ctx.restore();
      }});

      ctx.restore();
    }}

    // ----------------------------------------------------
    // MODE 4: NEURAL ORGANIC GRAPH (Constellations)
    // ----------------------------------------------------
    function renderGraphMode() {{
      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(scale, scale);

      // Flowing Bezier Streams
      DATA.links.forEach(l => {{
        const p1 = graphCoords.get(l.source);
        const p2 = graphCoords.get(l.target);
        if (!p1 || !p2) return;

        ctx.strokeStyle = isDarkTheme ? "rgba(56, 189, 248, 0.35)" : "rgba(2, 132, 199, 0.35)";
        ctx.lineWidth = Math.max(1, 1.6 / scale);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        // Flow particle
        const t = (animTime * 0.4) % 1.0;
        const px = p1.x + (p2.x - p1.x) * t;
        const py = p1.y + (p2.y - p1.y) * t;
        ctx.fillStyle = isDarkTheme ? "#38bdf8" : "#0284c7";
        ctx.beginPath();
        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx.fill();
      }});

      // Draw Neural Nodes
      DATA.nodes.forEach(node => {{
        const pt = graphCoords.get(node.id);
        if (!pt) return;

        const screenX = panX + pt.x * scale;
        const screenY = panY + pt.y * scale;
        const radius = (scale < 0.6 ? 22 : 30) * (hoveredNode?.id === node.id ? 1.2 : 1.0);
        screenNodeMap.set(node.id, {{ x: screenX, y: screenY, radius: radius * scale, visible: true }});

        renderFileBadgeNode(node, pt.x, pt.y, scale);
      }});

      ctx.restore();
    }}

    // ----------------------------------------------------
    // UNIVERSAL FILE BADGE NODE RENDERER
    // ----------------------------------------------------
    function renderFileBadgeNode(node, x, y, currScale) {{
      const isHovered = hoveredNode && hoveredNode.id === node.id;
      const isActive = activeNode && activeNode.id === node.id;
      const ftype = getFileType(node.name || node.id);
      const iconImg = iconImageCache.get(ftype.key);

      ctx.save();
      ctx.translate(x, y);

      let size = currScale < 0.55 ? 26 : 34;
      if (isHovered || isActive) size += 6;
      const half = size / 2;

      // Soft Elevation Drop Shadow
      ctx.shadowColor = isDarkTheme ? "rgba(0, 0, 0, 0.6)" : "rgba(15, 23, 42, 0.12)";
      ctx.shadowBlur = isHovered || isActive ? 14 : 6;
      ctx.shadowOffsetY = 2;

      // Badge Background
      ctx.fillStyle = ftype.bg;
      ctx.beginPath();
      ctx.roundRect(-half, -half, size, size, 7);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.shadowOffsetY = 0;

      // Icon Graphic / SVG
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

      // Blast Radius Border (Zero continuous annoying waves!)
      let strokeColor = isDarkTheme ? "rgba(255, 255, 255, 0.2)" : "rgba(255, 255, 255, 0.85)";
      let strokeWidth = 1.2;
      if (node.tier === 0) {{
        strokeColor = "#f43f5e";
        strokeWidth = 2.4;
      }} else if (node.tier === 1) {{
        strokeColor = "#f59e0b";
        strokeWidth = 2.0;
      }} else if (isHovered || isActive) {{
        strokeColor = isDarkTheme ? "#38bdf8" : "#0f172a";
        strokeWidth = 1.8;
      }}
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = strokeWidth;
      ctx.stroke();

      // Corner Status Pip
      if (node.tier === 0) {{
        ctx.beginPath();
        ctx.arc(half - 2, -half + 2, 4.5, 0, Math.PI * 2);
        ctx.fillStyle = "#e11d48";
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }} else if (node.tier === 1) {{
        ctx.beginPath();
        ctx.arc(half - 2, -half + 2, 4, 0, Math.PI * 2);
        ctx.fillStyle = "#ea580c";
        ctx.fill();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }}

      // Hover Micro-Sheen
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

      // File Label Below
      if (currScale > 0.45 || isHovered || isActive) {{
        ctx.fillStyle = isHovered || isActive ? (isDarkTheme ? "#f8fafc" : "#0f172a") : (isDarkTheme ? "#94a3b8" : "#334155");
        ctx.font = isHovered || isActive ? "600 12px -apple-system, sans-serif" : "500 11px -apple-system, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillText(node.name, 0, half + 5);

        if (node.tier === 0 && (currScale > 0.65 || isHovered)) {{
          const diffStr = (node.added > 0 || node.deleted > 0) ? `+${{node.added}} -${{node.deleted}}` : "EDITED";
          ctx.fillStyle = "#f43f5e";
          ctx.font = "bold 9px -apple-system, sans-serif";
          ctx.fillText(diffStr, 0, half + 19);
        }}
      }}

      ctx.restore();
    }}

    // ==========================================
    // TIMELINE FLIGHT SCRUBBER
    // ==========================================
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

        if (st.file) {{
          flyToNode(st.file);
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

    function toggleHistoryDrawer() {{
      const drw = document.getElementById("historyDrawer");
      drw?.classList.toggle("translate-y-[200%]");
    }}

    // Initial setup
    fitToScreen();
    requestAnimationFrame(draw);
    if (DATA.steps.length) setStep(0);
  </script>
</body>
</html>
"""
    return html

def main():
    parser = argparse.ArgumentParser(description="Code Earth - Unified Multi-Perspective Visualizer")
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

    print(f"[+] Code Earth multi-view visualizer generated at: {out_p}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
