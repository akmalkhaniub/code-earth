---
name: flight-deck
description: Visualizes the agent's changes as an interactive, zoomable module dependency graph showing blast radius (Tier 0 epicenter, Tier 1 direct ripple, Tier 2 transitive consumers), test pass/fail radar, and chronological execution path scrubber from transcript.jsonl. Use when the user asks to see a visual graph of files, inspect blast radius, or review the agent's work.
---

# Agent Flight Deck & Blast Radius Visualizer

This skill generates a self-contained interactive web deck visualizing:
1. **Module Hierarchy & Spatial Zoom**: Groups files by packages/folders; zoom in/out from high-level architecture down to individual files.
2. **Blast Radius Analysis**:
   - 🔴 **Tier 0 (Epicenter)**: Directly edited or generated files.
   - 🟠 **Tier 1 (Direct Ripple)**: Downstream files that directly import Tier 0.
   - 🟡 **Tier 2 (Transitive Ripple)**: Files that depend on Tier 1.
3. **Flight Recorder (Chronological Scrubber)**:
   - Ingests `transcript.jsonl` to replay the agent's trajectory step-by-step (read 👁️, edit ✏️, test ⚡) with thought popovers.
4. **Verification Radar**:
   - Shows test passes, failures, and flags untested modified files.

---

## How to Run

When the user asks to visualize changes or inspect the blast radius:

1. **Execute the Python Engine**:
   Run the bundled script passing the current workspace and the active transcript:

   ```powershell
   python "C:\Users\Silicon computer\.gemini\config\plugins\agent-flight-deck\skills\flight-deck\scripts\flight_deck_engine.py" --workspace "<workspace_dir>" --transcript "<transcript_path>" --output "<artifact_dir>\flight_deck.html"
   ```

2. **Embed Inline in Chat**:
   Render the generated artifact using:

   ```html
   <agent-embed src="file:///<artifact_dir>/flight_deck.html"></agent-embed>
   ```

3. **Provide Summary**:
   Highlight the count of Tier 0 (modified), Tier 1 (direct dependents), and Tier 2 (transitive) files, along with any untested blast radius alerts.
