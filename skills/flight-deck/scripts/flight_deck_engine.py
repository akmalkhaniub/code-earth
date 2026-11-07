#!/usr/bin/env python3
"""
Code Earth - Planetary Topographic Semantic Zoom Engine
Visualizes a codebase as a living, organic digital planet:
- Organic Tectonic Continents with topographic elevation contours (no rectangular boxes!)
- Seismic Epicenters with animated shockwaves and blast radius particle highways
- Floating In-Situ Telemetry Reticles (zero screen-blocking drawers)
- Topographic Code Strata etched directly into the bedrock on ground zoom
- Antigravity Flight Path timeline scrubber
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
    """Generates the organic topographic Code Earth canvas visualization."""

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
      background: radial-gradient(circle at 50% 50%, #060913 0%, #010307 100%);
      color: #f1f5f9;
      font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
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
    .hud-glass {{
      background: rgba(10, 15, 29, 0.75);
      backdrop-filter: blur(14px);
      border: 1px solid rgba(56, 189, 248, 0.15);
      box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    }}
    /* Custom scroll */
    ::-webkit-scrollbar {{ width: 4px; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(56, 189, 248, 0.3); border-radius: 4px; }}
  </style>
</head>
<body class="w-screen h-screen">

  <!-- TOP MINIMALIST HUD (Planet Status & Altitude) -->
  <header class="absolute top-4 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
    
    <!-- Planetary Condition -->
    <div class="hud-glass rounded-full px-5 py-2.5 flex items-center gap-4 pointer-events-auto">
      <div class="flex items-center gap-2.5">
        <span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399] animate-pulse"></span>
        <span class="font-bold text-xs tracking-wider text-slate-100 uppercase">Code Earth</span>
        <span class="text-slate-500 text-xs">/</span>
        <span class="text-slate-300 text-xs font-mono">{repo_name}</span>
      </div>

      <div class="h-4 w-px bg-slate-700/80"></div>

      <!-- Seismic Blast Status -->
      <div class="flex items-center gap-3.5 text-xs">
        <div class="flex items-center gap-1.5" title="Direct Epicenter Edits">
          <span class="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_#f43f5e] animate-ping"></span>
          <span class="font-bold text-rose-300" id="stat-epicenter">0</span>
          <span class="text-slate-400 text-[11px]">Epicenter</span>
        </div>
        <div class="flex items-center gap-1.5" title="Direct Ripple Consumers">
          <span class="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_6px_#fbbf24]"></span>
          <span class="font-bold text-amber-300" id="stat-ripple">0</span>
          <span class="text-slate-400 text-[11px]">Ripple</span>
        </div>
        <div class="flex items-center gap-1.5" title="Verified Safe Zones">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span class="font-bold text-emerald-300" id="stat-safe">0</span>
          <span class="text-slate-400 text-[11px]">Safe</span>
        </div>
      </div>
    </div>

    <!-- Altitude Orbit Jumpers & Fullscreen -->
    <div class="hud-glass rounded-full px-3 py-1.5 flex items-center gap-1 pointer-events-auto">
      <button onclick="setAltitude(0.28)" class="px-3 py-1 hover:bg-sky-500/10 rounded-full text-slate-300 hover:text-sky-300 text-xs font-medium transition" title="Global Planet Orbit">
        🛰️ Orbit
      </button>
      <button onclick="setAltitude(0.85)" class="px-3 py-1 hover:bg-sky-500/10 rounded-full text-slate-300 hover:text-sky-300 text-xs font-medium transition" title="Continent / Module">
        🧭 Continent
      </button>
      <button onclick="setAltitude(2.8)" class="px-3 py-1 bg-sky-500/20 text-sky-300 border border-sky-500/30 rounded-full text-xs font-bold transition" title="Topographic Ground Code">
        🔬 Code Strata
      </button>
      <button onclick="resetCamera()" class="p-1.5 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white text-xs ml-1" title="Reset Camera">
        ↺
      </button>
      <button onclick="toggleFullScreen()" class="px-2.5 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 rounded-full text-xs font-semibold transition ml-1 flex items-center gap-1" title="Toggle Full Screen (F11)">
        ⛶ Fullscreen
      </button>
    </div>
  </header>

  <!-- 100% FULLSCREEN TOPOGRAPHIC CANVAS -->
  <canvas id="earthCanvas" class="w-full h-full"></canvas>

  <!-- BOTTOM AMBIENT FLIGHT RECORDER (Non-Intrusive) -->
  <footer class="absolute bottom-4 left-6 right-6 z-20 flex flex-col gap-2 pointer-events-none items-center">
    
    <!-- In-flight Thought Bubble -->
    <div id="thoughtPill" class="hud-glass rounded-full px-5 py-2 max-w-xl w-full flex items-center justify-between gap-3 pointer-events-auto shadow-2xl transition-all duration-300">
      <div class="flex items-center gap-2.5 min-w-0">
        <span id="flightStep" class="px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-400 font-mono font-bold text-[10px]">Step 1</span>
        <p id="flightThought" class="text-slate-300 text-xs truncate">Exploring global topographic architecture...</p>
      </div>
      <span id="flightAction" class="text-[9px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-sky-300 uppercase tracking-widest">IDLE</span>
    </div>

    <!-- Minimalist Scrubber Ribbon -->
    <div class="hud-glass rounded-full px-4 py-2 w-full max-w-2xl flex items-center gap-3 pointer-events-auto">
      <button id="btnPlay" onclick="togglePlay()" class="w-7 h-7 rounded-full bg-sky-500/20 hover:bg-sky-500/40 text-sky-300 border border-sky-500/30 flex items-center justify-center font-bold text-xs transition">
        ▶
      </button>
      <span class="text-slate-400 font-mono text-[11px] min-w-[50px]" id="stepCount">0 / 0</span>
      <div class="flex-1 relative flex items-center">
        <input id="timeline" type="range" min="0" max="1" value="0" step="1" 
               class="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-400 focus:outline-none">
      </div>
      <button onclick="stepDelta(-1)" class="p-1 hover:text-white text-slate-400 text-xs">◀</button>
      <button onclick="stepDelta(1)" class="p-1 hover:text-white text-slate-400 text-xs">▶</button>
    </div>
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
    let scale = 0.32;
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
    const continentSpacingX = 950;
    const continentSpacingY = 800;

    // Generate organic coastline polygons with harmonic noise
    moduleList.forEach((modName, mi) => {{
      const col = mi % cols;
      const row = Math.floor(mi / cols);
      const cx = (col - cols / 2 + 0.5) * continentSpacingX;
      const cy = (row - Math.ceil(moduleList.length / cols) / 2 + 0.5) * continentSpacingY;

      const files = DATA.modules[modName];
      const baseRadius = Math.max(220, Math.sqrt(files.length) * 125);

      // Create organic contour vertices
      const numPoints = 32;
      const coastlinePoints = [];
      for (let i = 0; i < numPoints; i++) {{
        const theta = (i / numPoints) * Math.PI * 2;
        // Harmonic organic perturbation
        const rNoise = baseRadius * (1.0 + 0.14 * Math.sin(theta * 3 + mi) + 0.08 * Math.cos(theta * 5 - mi * 2));
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

      // Position file beacons within the continent
      files.forEach((fpath, fi) => {{
        const angle = (fi / files.length) * Math.PI * 2 + (mi * 0.4);
        const dist = Math.min(baseRadius - 70, (fi + 1) * 55);
        nodeCoords.set(fpath, {{
          x: cx + Math.cos(angle) * dist,
          y: cy + Math.sin(angle) * dist
        }});
      }});
    }});

    // Animation Clock
    let animTime = 0;

    // Mouse & Zoom
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
        panX = e.clientX - startX;
        panY = e.clientY - startY;
      }} else {{
        // Hit test for beacons
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

    function toggleFullScreen() {{
      if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen().catch(err => {{
          window.open(window.location.href, '_blank');
        }});
      }} else {{
        if (document.exitFullscreen) {{
          document.exitFullscreen();
        }}
      }}
    }}

    function setAltitude(s) {{
      scale = s;
    }}

    function resetCamera() {{
      scale = 0.32;
      panX = width / 2;
      panY = height / 2;
      activeNode = null;
    }}

    // MAIN RENDER LOOP (60fps)
    function draw() {{
      animTime += 0.025;
      ctx.clearRect(0, 0, width, height);

      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(scale, scale);

      // ==========================================
      // 1. ORGANIC TECTONIC CONTINENTS & CONTOURS
      // ==========================================
      continentLayout.forEach((cont, modName) => {{
        const pts = cont.points;
        if (!pts.length) return;

        // Outer Oceanic Shelf Glow
        const shelfGrad = ctx.createRadialGradient(cont.cx, cont.cy, cont.baseRadius * 0.3, cont.cx, cont.cy, cont.baseRadius * 1.3);
        shelfGrad.addColorStop(0, cont.hasEpicenter ? "rgba(244, 63, 94, 0.12)" : "rgba(14, 165, 233, 0.08)");
        shelfGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = shelfGrad;
        ctx.beginPath();
        ctx.arc(cont.cx, cont.cy, cont.baseRadius * 1.3, 0, Math.PI * 2);
        ctx.fill();

        // Organic Landmass Bedrock
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
        ctx.fillStyle = "rgba(10, 15, 29, 0.85)";
        ctx.fill();

        // Glowing Coastline
        ctx.strokeStyle = cont.hasEpicenter ? "rgba(244, 63, 94, 0.6)" : "rgba(56, 189, 248, 0.4)";
        ctx.lineWidth = 2 / scale;
        ctx.shadowColor = cont.hasEpicenter ? "#f43f5e" : "#38bdf8";
        ctx.shadowBlur = 12;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Concentric Topographic Elevation Contours (Internal Strata)
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
            `rgba(251, 146, 60, ${{0.15 - idx * 0.03}})` : 
            `rgba(56, 189, 248, ${{0.12 - idx * 0.02}})`;
          ctx.lineWidth = 1 / scale;
          ctx.stroke();
        }});

        // Topographic Continent Label
        if (scale < 1.4) {{
          ctx.fillStyle = cont.hasEpicenter ? "rgba(254, 205, 211, 0.9)" : "rgba(148, 163, 184, 0.75)";
          ctx.font = `700 ${{Math.max(14, 22)}}px ui-sans-serif, system-ui`;
          ctx.textAlign = "center";
          ctx.fillText(`⯎ ${{modName.toUpperCase()}}`, cont.cx, cont.cy - cont.baseRadius - 16);
        }}
      }});

      // ==========================================
      // 2. DEPENDENCY HIGHWAYS & PHOTON STREAMS
      // ==========================================
      DATA.links.forEach(l => {{
        const src = nodeCoords.get(l.source);
        const tgt = nodeCoords.get(l.target);
        if (!src || !tgt) return;

        const srcNode = DATA.nodes.find(n => n.id === l.source);
        const isEpicenterEdge = srcNode && srcNode.tier === 0;

        // Smooth curved energy river
        const midX = (src.x + tgt.x) / 2 - (tgt.y - src.y) * 0.15;
        const midY = (src.y + tgt.y) / 2 + (tgt.x - src.x) * 0.15;

        ctx.strokeStyle = isEpicenterEdge ? "rgba(244, 63, 94, 0.35)" : "rgba(56, 189, 248, 0.18)";
        ctx.lineWidth = Math.max(1, 1.4 / scale);
        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.quadraticCurveTo(midX, midY, tgt.x, tgt.y);
        ctx.stroke();

        // Flowing energy photon
        const t = (animTime * 0.6) % 1.0;
        const px = (1 - t) ** 2 * src.x + 2 * (1 - t) * t * midX + t ** 2 * tgt.x;
        const py = (1 - t) ** 2 * src.y + 2 * (1 - t) * t * midY + t ** 2 * tgt.y;

        ctx.beginPath();
        ctx.arc(px, py, isEpicenterEdge ? 3.5 : 2.5, 0, Math.PI * 2);
        ctx.fillStyle = isEpicenterEdge ? "#f43f5e" : "#38bdf8";
        ctx.shadowColor = isEpicenterEdge ? "#f43f5e" : "#38bdf8";
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;
      }});

      // ==========================================
      // 3. SEISMIC BEACONS & SHOCKWAVE PULSES
      // ==========================================
      DATA.nodes.forEach(node => {{
        const pt = nodeCoords.get(node.id);
        if (!pt) return;

        const isHovered = hoveredNode && hoveredNode.id === node.id;
        const isActive = activeNode && activeNode.id === node.id;

        let beaconColor = "#38bdf8";
        if (node.tier === 0) beaconColor = "#f43f5e"; // Epicenter Red
        else if (node.tier === 1) beaconColor = "#fbbf24"; // Direct Ripple Amber
        else if (node.tier === 2) beaconColor = "#fde047"; // Transitive Yellow

        // A. Seismic Epicenter Expanding Shockwave Rings
        if (node.tier === 0) {{
          for (let w = 0; w < 3; w++) {{
            const waveProgress = ((animTime * 0.8 + w * 0.33) % 1.0);
            const waveRadius = 15 + waveProgress * 95;
            const waveOpacity = (1.0 - waveProgress) * 0.7;

            ctx.beginPath();
            ctx.arc(pt.x, pt.y, waveRadius, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(244, 63, 94, ${{waveOpacity}})`;
            ctx.lineWidth = 2 / scale;
            ctx.stroke();
          }}
        }}

        // B. Ground Code Strata (Scale > 1.8: No rectangles, pure etched code!)
        if (scale >= 1.8) {{
          ctx.save();
          ctx.translate(pt.x, pt.y);

          // Topographic Strata Boundary (soft glowing halo)
          ctx.fillStyle = "rgba(4, 8, 18, 0.92)";
          ctx.beginPath();
          ctx.arc(0, 0, 160, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = isHovered || isActive ? "#ffffff" : beaconColor;
          ctx.lineWidth = 1.5 / scale;
          ctx.stroke();

          // Filename Inscription
          ctx.fillStyle = "#ffffff";
          ctx.font = "bold 13px ui-sans-serif, system-ui";
          ctx.textAlign = "center";
          ctx.fillText(node.name, 0, -125);

          // In-Situ Code Lines
          ctx.font = "10px monospace";
          ctx.textAlign = "left";
          const lines = node.diffLines && node.diffLines.length ? node.diffLines.slice(0, 11) : (node.codeLines || []).slice(0, 11);
          let ly = -95;

          lines.forEach(l => {{
            if (l.type === "add") {{
              ctx.fillStyle = "rgba(52, 211, 153, 0.18)";
              ctx.fillRect(-135, ly - 9, 270, 14);
              ctx.fillStyle = "#34d399";
              ctx.fillText(`+ ${{l.text.slice(0, 36)}}`, -130, ly + 2);
            }} else if (l.type === "del") {{
              ctx.fillStyle = "rgba(248, 113, 113, 0.18)";
              ctx.fillRect(-135, ly - 9, 270, 14);
              ctx.fillStyle = "#f87171";
              ctx.fillText(`- ${{l.text.slice(0, 36)}}`, -130, ly + 2);
            }} else {{
              ctx.fillStyle = "#94a3b8";
              const txt = l.text !== undefined ? l.text : l;
              ctx.fillText(`  ${{String(txt).slice(0, 36)}}`, -130, ly + 2);
            }}
            ly += 16;
          }});

          ctx.restore();
        }}
        // C. Celestial Beacon Orb (Scale < 1.8)
        else {{
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, isHovered || isActive ? 14 : 9, 0, Math.PI * 2);
          ctx.fillStyle = beaconColor;
          ctx.shadowColor = beaconColor;
          ctx.shadowBlur = isHovered || isActive ? 16 : 8;
          ctx.fill();
          ctx.shadowBlur = 0;

          // Ambient Filename Label
          if (scale > 0.55 || isHovered || isActive) {{
            ctx.fillStyle = isHovered || isActive ? "#ffffff" : "rgba(241, 245, 249, 0.85)";
            ctx.font = isHovered || isActive ? "bold 12px ui-sans-serif" : "11px ui-sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(node.name, pt.x, pt.y + 20);
          }}
        }}

        // ==========================================
        // 4. IN-SITU HUD TELEMETRY RETICLE (Zero Drawers!)
        // ==========================================
        if (isHovered || isActive) {{
          ctx.save();
          ctx.translate(pt.x, pt.y);

          // Targeting Ring
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 1.5 / scale;
          ctx.beginPath();
          ctx.arc(0, 0, 24, 0, Math.PI * 2);
          ctx.stroke();

          // Crosshairs
          ctx.setLineDash([4 / scale, 4 / scale]);
          ctx.beginPath();
          ctx.moveTo(-32, 0); ctx.lineTo(32, 0);
          ctx.moveTo(0, -32); ctx.lineTo(0, 32);
          ctx.stroke();
          ctx.setLineDash([]);

          // Floating Telemetry Halo
          const boxX = 35;
          const boxY = -45;
          ctx.fillStyle = "rgba(10, 15, 29, 0.9)";
          ctx.strokeStyle = beaconColor;
          ctx.lineWidth = 1.2 / scale;
          ctx.beginPath();
          ctx.roundRect(boxX, boxY, 150, 60, 8);
          ctx.fill();
          ctx.stroke();

          // HUD Leader Line
          ctx.beginPath();
          ctx.moveTo(18, -18);
          ctx.lineTo(boxX, boxY + 20);
          ctx.stroke();

          // Telemetry Data
          ctx.fillStyle = "#ffffff";
          ctx.font = "bold 11px ui-sans-serif";
          ctx.textAlign = "left";
          ctx.fillText(node.name, boxX + 10, boxY + 18);

          ctx.font = "10px monospace";
          ctx.fillStyle = node.tier === 0 ? "#f43f5e" : (node.tier === 1 ? "#fbbf24" : "#38bdf8");
          const tierLabel = node.tier === 0 ? "⚡ EPICENTER" : (node.tier === 1 ? "▲ RIPPLE ZONE" : "✓ SAFE NODE");
          ctx.fillText(tierLabel, boxX + 10, boxY + 34);

          ctx.fillStyle = "#94a3b8";
          let statText = "";
          if (node.added > 0 || node.deleted > 0) {{
            statText = `+${{node.added}} -${{node.deleted}} Git Diff | ${{node.inbound.length}} callers`;
          }} else if (node.tier === 0) {{
            statText = `Active Session Edit | ${{node.inbound.length}} callers`;
          }} else if (node.tier === 1) {{
            statText = `Imports Epicenter | ${{node.inbound.length}} callers`;
          }} else {{
            statText = `Clean Bedrock | ${{node.inbound.length}} callers`;
          }}
          ctx.fillText(statText, boxX + 10, boxY + 48);

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

    // Start 60fps Loop
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
