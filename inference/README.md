# Inference Pipeline

The public inference pipeline extracts skill-like phrases from job-description text and links them to skills in the runtime taxonomy.

## Runtime Input

By default, `PublicEntityLinker` reads:

- `inference/files/skills_ca.csv`

You can override this with the `skills_path` argument.

## Usage

Run from the repository root with your virtual environment active.

```python
from inference.public_entity_linker import PublicEntityLinker

pipeline = PublicEntityLinker()
text = "We are looking for a Head Chef who can plan menus."
extracted = pipeline.link_and_group(text, threshold=0.40, top_k_candidates=100)
print(extracted)
```

Example output shape:

```python
[
    {
        "type": "Skill",
        "skill": "plan menus",
        "code": "<optional code>",
        "score": 0.98,
        "mentions": ["plan menus"],
    }
]
```

## CLI Usage

`public_entity_linker.py` also supports CLI usage:

```bash
python3 inference/public_entity_linker.py \
  --text "We are looking for a Head Chef who can plan menus." \
  --threshold 0.40 \
  --top-k-candidates 100
```

Optional flags:

- `--skills-path`
- `--model-id`
- `--threshold`
- `--top-k-candidates`
