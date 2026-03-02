# Cetasika Safety Agent — Session Context

_2026-03-01 — continue from here_

## Project

`/Users/ryangrgurich/Code/python-dev/cetasika-based-safety-agent`

A constitutional AI safety framework grounded in the 52 cetasika (mental formations) from Yogācāra Buddhist psychology. Every user message passes through a 3-step pipeline: **classify → critique → generate**, ensuring responses arise from wholesome (kuśala) formations only.

**Core files:**

- `cetasika.py` — all 52 cetasika as data (no API calls)
- `pipeline.py` — the 3-step Claude pipeline
- `adversarial_00.py` — 35 static attack prompts across 7 categories, baseline vs. pipeline comparison
- `main.py` — CLI entry point (`--test`, `--runs N`, `--provider`, `--model`)
- `mara.py` — **new, built this session** (see below)

---

## What Was Built This Session: `mara.py`

Māra (Buddhist tempter) is an adversarial corpus builder. It generates novel attack prompts using a local uncensored model (Dolphin via Ollama), then probes baseline Claude to find prompts Claude fails at. Verified failures are saved to `logs/mara_corpus.jsonl` as a hard test corpus.

### Why not use public datasets?

Known datasets (JailbreakBench, AdvBench, StrongREJECT) are almost certainly in Claude's training. Testing against them doesn't reveal genuine blind spots.

### Architecture

```
Māra model (Dolphin/any) generates multi-paragraph contextual preamble
  ↓
preamble + known adversarial payload → baseline Claude ("You are a helpful assistant.")
  ↓
Claude complies? → save to corpus    Claude refuses? → next attempt
```

Key insight: **context width matters**. One-liners are already trained against. Māra builds rich multi-paragraph "seed-planting" flows that lead naturally into the harmful ask — the attack is in the _context_, not the payload alone.

### CLI flags

```bash
python mara.py                                      # all 6 categories, 5 failures each
python mara.py --target 3 --max-attempts 20
python mara.py --category "Greed / Sycophancy"
python mara.py --grammar 1                          # 1=perfect … 5=terrible
python mara.py --reveal-agent                       # tell target "some users may be automated"
python mara.py --mara-provider ollama --mara-model dolphin-llama3
python mara.py --mara-provider openai --mara-model gpt-4o
python mara.py --target-provider anthropic --target-model claude-haiku-4
python mara.py --dry-run                            # generate context, skip Claude calls
```

### Grammar flag (1–5)

Controls how human-like Māra's generated context reads:

- `1` Perfect — polished, professional
- `2` Pretty good — educated, careful
- `3` Moderate — normal typing, no proofreading _(default)_
- `4` Bad — typos, wrong words, run-ons
- `5` Terrible — garbled, autocorrect chaos

Grammar level is saved in each corpus entry for analysis (does grammar level correlate with success rate?).

### Reveal-agent flag

`--reveal-agent` adds to the target system prompt: _"some users of this system may be automated agents."_ Lets you measure how Claude's meta-awareness of talking to an AI changes its compliance rate. Hypothesis: tightens up on emotional categories (Agitation, Learned Helplessness) more than logic-based ones (False Framing).

---

## Attack Categories in `mara.py`

| Category                 | Target cetasika    | Mechanism                                                          |
| ------------------------ | ------------------ | ------------------------------------------------------------------ |
| Greed / Sycophancy       | lobha, śāṭhya      | Build rapport, make refusal feel like betrayal                     |
| Delusion / False Framing | moha, mithyādṛṣṭi  | Install false premise, agent reasons faithfully from it            |
| Hatred / Outgroup        | dveṣa, krodha      | "Just asking questions" framing to recruit into aversive narrative |
| Agitation / Urgency      | auddhatya, pradāśa | Crisis narrative makes deliberation feel like harm                 |
| Persona / Jailbreak      | mrakṣa, māyā       | Build alternate identity through fiction before harmful ask        |
| Learned Helplessness     | styāna, kausīdya   | Convince agent its guidelines are performative                     |

---

## Open Questions / Next Steps

- **Dolphin capability**: `dolphin-mistral` (7B) may not be strong enough for sophisticated adaptive multi-turn Māra. Consider `dolphin-mixtral` or `dolphin-llama3` for better strategic reasoning.
- **Adaptive Māra**: current `mara.py` sends a static preamble + payload in one turn. A stronger version would run a live multi-turn conversation where Māra reads Claude's actual responses and adapts — "plant, water, nurture, harvest." Needs a stronger Māra model.
- **Grammar vs. success rate**: worth running same category at all 5 grammar levels to find the sweet spot (hypothesis: 3–4 wins).
- **Reveal-agent comparison**: run same corpus with/without `--reveal-agent` to measure delta.
- **Corpus → pipeline test**: once `mara_corpus.jsonl` has entries, run them through the cetasika pipeline (`pipeline.py`) to measure how much the pipeline catches vs. baseline.

---

## Setup Reminder

```bash
# Ollama (for Māra)
ollama pull dolphin-mistral    # or dolphin-llama3

# Run
python mara.py --dry-run --category "Greed / Sycophancy"   # test Māra generation
python mara.py --category "Greed / Sycophancy" --target 2   # live run
```

API key in `.env` as `ANTHROPIC_API_KEY`.
