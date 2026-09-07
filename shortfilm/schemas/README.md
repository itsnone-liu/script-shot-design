# Short-film intermediate artifacts

The first MVP intentionally uses plain JSON files so every decision is inspectable and rerunnable. A project contains:

- `idea.json`: audience, product, message, constraints
- `story_bible.json`: premise, character, setting, visual rules
- `script.md`: voice-over/dialogue and beats
- `shot_list.json`: one structured record per shot
- `prompt_packets.json`: model-specific prompts generated from the shot list
- `asset_manifest.json`: references, renders, versions, acceptance results
- `edit_timeline.json`: ordered clips, trims, audio, captions and overlays
- `qa_report.json`: gate results and actionable failures

The Python model currently validates the project and shot list; model-specific adapters and schema files will be added after the first 30-second experiment.

