# 🌍 Code Earth

> **"Google Earth for Code"** — An AI coding assistant plugin and topographic visualizer that replaces raw textual diff walls (`+10, -20`) with an organic digital planet. Visualize architectural boundaries, animated seismic blast-radius shockwaves, and zoom seamlessly from orbit down to syntax-highlighted code strata.

---

## 🌟 Key Capabilities

1. **Organic Tectonic Continents (No Boxy UI Cards)**:
   - Packages and modules are rendered as **organic landmasses with elevation contours** and oceanic shelf glows.
   - Eliminates cluttered rectangular frames in favor of natural topological clusters.

2. **Seismic Blast Radius Shockwaves (The 1-Second High-Level Picture)**:
   - **The Epicenter 🔴**: Any file modified by an AI agent pulses with **concentric shockwave rings**.
   - **Energy Rivers & Photons**: Curved dependency highways carry flowing particle streams from the epicenter to downstream consumers (Amber 🟠) and safe zones (Emerald 🟢).
   - Instant visual clarity on whether an edit is an isolated leaf or a foundational risk.

3. **In-Situ Telemetry Reticle (Zero Screen-Blocking Drawers)**:
   - Hovering or clicking a beacon locks an animated **targeting ring** with floating telemetry pills directly in world space.
   - 100% of the map remains visible and interactive.

4. **Infinite Semantic Zoom (LOD 1 to 4)**:
   - **🛰️ Level 1 (Space Orbit)**: Global continent map and blast heat zones.
   - **🧭 Level 2 (Continent View)**: File landmasses and dependency highways.
   - **🏢 Level 3 (District View)**: AST class & function anatomy blueprints.
   - **🔬 Level 4 (Ground Level)**: In-situ **syntax-highlighted code and git diff hunks** (+ green, - red) etched directly onto the bedrock.

5. **Agent Flight Recorder**:
   - Replays the agent's chronological execution path (read 👁️, edit ✏️, test ⚡) with camera tracking and thought stream popovers.

---

## 🚀 Quick Start

### Running with Antigravity
Code Earth is a native Antigravity plugin. Once installed, simply ask:
- *"Open Code Earth to visualize repository architecture"*
- *"Show blast radius and seismic shockwaves of recent edits"*
- *"Launch agent flight deck"*

### Running as Standalone CLI
You can generate a standalone HTML visualizer for any codebase:

```bash
python skills/flight-deck/scripts/flight_deck_engine.py \
  --workspace "/path/to/repo" \
  --output "code_earth.html"
```

Open `code_earth.html` in any browser or click `⛶ Fullscreen` (or press `F11`) for a borderless canvas experience.

---

## 🏗️ Architecture

```text
code-earth/
├── plugin.json                              # Antigravity plugin manifest
├── rules/
│   └── AGENTS.md                            # Agent instructions for automated invocation
├── sidecars/
│   └── flight_deck/
│       ├── sidecar.json                     # Antigravity Sidecar UI configuration
│       └── ui.html                          # Standalone Code Earth HTML canvas
└── skills/
    └── flight-deck/
        ├── SKILL.md                         # Skill definition & execution instructions
        └── scripts/
            └── flight_deck_engine.py        # Python AST, Git & Transcript parser
```

---

## 📜 License
MIT License. Created by Akmal Khan.
