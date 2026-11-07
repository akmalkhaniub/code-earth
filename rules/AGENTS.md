# Agent Flight Deck Guidelines

Whenever completing a multi-file refactoring, substantial code generation, or when the user asks to see a visual overview of changes or blast radius:
1. Run `flight_deck_engine.py` to produce `flight_deck.html` in the artifact directory.
2. Render `<agent-embed src="file:///<artifact_dir>/flight_deck.html"></agent-embed>` in chat so the user can interactively zoom, inspect module ripple effects, and scrub through the flight path.
