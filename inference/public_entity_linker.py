from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import pandas as pd
from sentence_transformers import SentenceTransformer, util


# for context setting for stop words
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}

# Single-word mentions that are often context-dependent (skill vs task/action)
AMBIGUOUS_SINGLE_WORDS = {
    "drive",
    "help",
    "lead",
    "manage",
    "monitor",
    "push",
    "support",
    "test",
    "work",
}

# Cues used to keep only labels that look like soft/interpersonal skills
SOFT_SKILL_LABEL_CUES = {
    "adapt",
    "adaptability",
    "analysis",
    "analytical",
    "assert",
    "assertive",
    "attention to detail",
    "autonomy",
    "collaborat",
    "communicat",
    "conflict",
    "cooperat",
    "creative",
    "creativity",
    "critical thinking",
    "customer service",
    "decision",
    "detail",
    "empathy",
    "ethic",
    "facilitat",
    "flexib",
    "initiative",
    "interpersonal",
    "leadership",
    "listen",
    "judg",
    "mentoring",
    "motivat",
    "negotiat",
    "organiz",
    "patience",
    "persuasion",
    "planning",
    "presentation",
    "priorit",
    "problem solving",
    "professional",
    "professionalism",
    "relationship",
    "resilien",
    "responsib",
    "service orientation",
    "self-management",
    "self management",
    "social",
    "stress management",
    "team",
    "teamwork",
    "time management",
    "troubleshooting",
    "verbal",
    "written",
}

# Lead-in tokens that often precede capability phrases in job text
CAPABILITY_LEAD_INS = {
    "ability",
    "abilities",
    "capable",
    "capability",
    "demonstrate",
    "demonstrates",
    "demonstrated",
    "demonstrating",
    "effective",
    "excellent",
    "experience",
    "experienced",
    "proven",
    "skill",
    "skills",
    "strong",
}

# Connector tokens trimmed from phrase boundaries and phrase construction
CONNECTOR_WORDS = {
    "and",
    "as",
    "in",
    "of",
    "or",
    "to",
    "with",
}

# Tokens that indicate soft-skill context when intersected with sentence tokens
SOFT_SKILL_CONTEXT_CUES = {
    "ability",
    "adaptability",
    "analytical",
    "attitude",
    "collaborate",
    "collaboration",
    "communicate",
    "communication",
    "communicator",
    "creative",
    "creativity",
    "customer",
    "dependable",
    "detail",
    "empathy",
    "flexible",
    "initiative",
    "interpersonal",
    "judgment",
    "leadership",
    "listen",
    "listening",
    "mentor",
    "motivation",
    "organized",
    "patience",
    "presentation",
    "problem-solving",
    "problem",
    "professional",
    "professionalism",
    "relationship",
    "responsible",
    "self-management",
    "team",
    "teamwork",
    "troubleshooting",
    "verbal",
    "written",
}

# Tokens that indicate technical/task context to suppress false positives
TASK_CONTEXT_CUES = {
    "api",
    "branch",
    "build",
    "code",
    "coding",
    "commit",
    "deploy",
    "deployment",
    "docker",
    "engineering",
    "excel",
    "github",
    "git",
    "inventory",
    "javascript",
    "kpi",
    "linux",
    "merge",
    "python",
    "remote",
    "repository",
    "sales",
    "sql",
    "sprint",
    "target",
    "ticket",
}

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass
class LinkedSkill:
    mention: str
    skill: str
    code: Optional[str]
    score: float


@dataclass
class CandidatePhrase:
    phrase: str
    sentence: str
    token_count: int



# Public-only entity linker:
# 1) Extract candidate skill phrases from text
# 2) Link candidates to canonical skills using embedding similarity

class PublicEntityLinker:
    def __init__(
        self,
        skills_path = "inference/files/skills_ca.csv",
        model_id = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        df = pd.read_csv(skills_path)
        if "skills" not in df.columns:
            raise ValueError("skills file must contain a 'skills' column")

        # Normalizes and clean skill labels so downstream matching is stable
        df = df.copy()
        df["skills"] = df["skills"].astype(str).str.strip()
        df = df[df["skills"] != ""]
        df = df.drop_duplicates(subset=["skills"], keep="first")
        df["skill_norm"] = df["skills"].str.lower()
        # Keeps only labels that look like soft-skill names for this linker
        df = df[df["skill_norm"].apply(self._is_likely_soft_skill_label)]

        self.skills: List[str] = df["skills"].tolist()

        # Supports a few common code/id column names in different datasets
        code_column = None
        for candidate in ("code", "Code", "uuid", "UUID"):
            if candidate in df.columns:
                code_column = candidate
                break

        if code_column is not None:
            # Converts blank/NaN values to None for consistent downstream output
            self.codes = [
                str(value).strip() if pd.notna(value) and str(value).strip() else None
                for value in df[code_column]
            ]
        else:
            self.codes = [None] * len(self.skills)

        self.model = SentenceTransformer(model_id)
        # Precomputs canonical skill embeddings once; linking only encodes mentions
        self.skill_embeddings = self.model.encode(
            self.skills, convert_to_tensor=True, normalize_embeddings=True
        )


    @staticmethod
    # Heuristic filter to keep only labels that resemble soft-skill names
    def _is_likely_soft_skill_label(skill_label):
        label = skill_label.strip().lower()
        if not label:
            return False
        return any(cue in label for cue in SOFT_SKILL_LABEL_CUES)


    @staticmethod
    # Lowercase tokenization that preserves common tech tokens (e.g., C++, C#, API-like forms)
    def _tokenize(text):
        return re.findall(r"[A-Za-z][A-Za-z0-9+#/\.-]*", text.lower())


    @staticmethod
    # Splits text into sentence-like chunks while dropping empty fragments
    def _split_sentences(text):
        parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
        return parts if parts else [text.strip()]


    # Converts to a set to enable fast cue overlap checks via intersections
    @staticmethod
    def _context_tokens(text):
        return set(PublicEntityLinker._tokenize(text))

    @staticmethod
    # Compute a context-aware minimum similarity threshold for accepting a mention
    def _required_threshold(mention, base_threshold, sentence_tokens) :
        token_count = len(mention.split())
        threshold = base_threshold

        # Single-token mentions are noisier, so require a stronger match
        if token_count == 1:
            threshold = max(threshold, 0.53)

        if mention in AMBIGUOUS_SINGLE_WORDS:
            has_soft_skill_cue = bool(sentence_tokens & SOFT_SKILL_CONTEXT_CUES)
            has_task_cue = bool(sentence_tokens & TASK_CONTEXT_CUES)
            # Ambiguous words get a stricter default threshold
            threshold = max(threshold, 0.60)
            # Soft-skill context allows a moderate threshold
            if has_soft_skill_cue:
                threshold = max(base_threshold, 0.52)
            # Task-heavy context requires very high confidence
            if has_task_cue and not has_soft_skill_cue:
                threshold = max(threshold, 0.85)

        return threshold

    # Rule-based skip to reduce obvious false positives before embedding checks
    @staticmethod
    def _should_skip_candidate(mention, sentence_tokens):
        # Rule-based skip to reduce obvious false positives before embedding checks
        if mention in STOPWORDS:
            return True

        if mention in AMBIGUOUS_SINGLE_WORDS:
            has_soft_skill_cue = bool(sentence_tokens & SOFT_SKILL_CONTEXT_CUES)
            has_task_cue = bool(sentence_tokens & TASK_CONTEXT_CUES)
            if has_task_cue and not has_soft_skill_cue:
                return True

        return False


    # Builds phrases that follow capability lead-ins (e.g., "ability to ...")
    @staticmethod
    def _extract_capability_phrases_from_tokens(tokens):
        candidates: List[CandidatePhrase] = []
        max_window = min(len(tokens), 6)

        for i, token in enumerate(tokens):
            if token not in CAPABILITY_LEAD_INS:
                continue

            for j in range(i + 1, min(len(tokens), i + 1 + max_window)):
                window = tokens[i + 1 : j + 1]
                if not window:
                    continue
                if all(item in STOPWORDS or item in CONNECTOR_WORDS for item in window):
                    continue

                phrase_tokens = [
                    item for item in window if item not in STOPWORDS and item not in CONNECTOR_WORDS
                ]
                if not phrase_tokens:
                    continue

                phrase = " ".join(phrase_tokens).strip()
                if phrase:
                    candidates.append(
                        CandidatePhrase(
                            phrase=phrase,
                            sentence=" ".join(tokens),
                            token_count=len(phrase_tokens),
                        )
                    )
        return candidates


    # Extracts n-gram phrases and capability-led phrases from each sentence
    @staticmethod
    def _extract_sentence_skill_phrases(sentence, tokens):
        candidates: List[CandidatePhrase] = []

        for n in range(2, min(5, len(tokens)) + 1):
            for i in range(len(tokens) - n + 1):
                window = tokens[i : i + n]
                if all(token in STOPWORDS for token in window):
                    continue
                if window[0] in CONNECTOR_WORDS or window[-1] in CONNECTOR_WORDS:
                    continue

                phrase = " ".join(window).strip()
                if phrase:
                    candidates.append(
                        CandidatePhrase(
                            phrase=phrase,
                            sentence=sentence.strip(),
                            token_count=n,
                        )
                    )

        if any(token in CAPABILITY_LEAD_INS for token in tokens):
            candidates.extend(PublicEntityLinker._extract_capability_phrases_from_tokens(tokens))

        return candidates

    # Splits text into sentence-level candidate skill phrases and deduplicate by local context
    def extract_candidate_phrases(self, text):
        sentences = self._split_sentences(text)
        candidates: List[CandidatePhrase] = []

        for sentence in sentences:
            tokens = self._tokenize(sentence)
            if not tokens:
                continue
            candidates.extend(self._extract_sentence_skill_phrases(sentence, tokens))

        # Uses a set for fast duplicate checks while preserving first-seen order in `deduped`
        # Deduplicating on (phrase, sentence) keeps the phrase tied to its local context
        seen = set()
        deduped= []
        for candidate in candidates:
            key = (candidate.phrase, candidate.sentence)
            if key not in seen:
                seen.add(key)
                deduped.append(candidate)
        return deduped

    # Links extracted mentions to the closest canonical skill using cosine similarity
    def link(self, text, threshold, top_k_candidates):
        candidates = self.extract_candidate_phrases(text=text)
        if not candidates:
            return []

        # Caps candidate count to keep runtime bounded on long inputs
        if len(candidates) > top_k_candidates:
            candidates = candidates[:top_k_candidates]

        candidate_embeddings = self.model.encode(
            [candidate.phrase for candidate in candidates],
            convert_to_tensor=True,
            normalize_embeddings=True,
        )
        similarity = util.cos_sim(candidate_embeddings, self.skill_embeddings)

        links = []
        for row_index, candidate in enumerate(candidates):
            row = similarity[row_index]
            # Picsk the single best-matching canonical skill for this mention
            score, skill_index = row.max(dim=0)
            score_value = float(score.item())
            sentence_tokens = self._context_tokens(candidate.sentence)
            mention = candidate.phrase
            if self._should_skip_candidate(mention, sentence_tokens):
                continue

            # Applys context-aware acceptance threshold before keeping the link
            required_threshold = self._required_threshold(
                mention=mention,
                base_threshold=threshold,
                sentence_tokens=sentence_tokens,
            )
            if score_value >= required_threshold:
                links.append(
                    LinkedSkill(
                        mention=mention,
                        skill=self.skills[int(skill_index.item())],
                        code=self.codes[int(skill_index.item())],
                        score=round(score_value, 4),
                    )
                )
        return links

    # Merges per-mention links into one entry per canonical skill
    def link_and_group(self, text, threshold = 0.40, top_k_candidates= 100):
        links = self.link(
            text=text,
            threshold=threshold,
            top_k_candidates=top_k_candidates,
        )
        grouped = {}
        for item in links:
            if item.skill not in grouped:
                # First mention for this skill initializes the aggregate record
                grouped[item.skill] = {
                    "type": "Skill",
                    "skill": item.skill,
                    "code": item.code,
                    "score": item.score,
                    "mentions": [item.mention],
                }
            else:
                # Keeps all mentions, fill missing code, and preserve best score
                grouped[item.skill]["mentions"].append(item.mention)
                if grouped[item.skill]["code"] is None and item.code is not None:
                    grouped[item.skill]["code"] = item.code
                if item.score > grouped[item.skill]["score"]:
                    grouped[item.skill]["score"] = item.score

        results = list(grouped.values())
        # Returns highest-confidence skills first
        results.sort(key=lambda x: x["score"], reverse=True)
        return results


# Builds CLI arguments for running the linker from the terminal
def _build_parser():
    parser = argparse.ArgumentParser(
        description="Public entity linker for skill phrases."
    )
    parser.add_argument("--text", required=True, help="Job description text")
    parser.add_argument(
        "--skills-path",
        default="inference/files/skills_ca.csv",
        help="Path to skills csv with a 'skills' column and optional 'code' column",
    )
    parser.add_argument(
        "--model-id",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Sentence Transformer model id",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.40,
        help="Minimum cosine similarity for accepted links",
    )
    parser.add_argument(
        "--top-k-candidates",
        type=int,
        default=100,
        help="Maximum number of candidate phrases to consider",
    )
    return parser


# CLI entry point: run linking and print tab-separated results
def main():
    args = _build_parser().parse_args()
    linker = PublicEntityLinker(
        skills_path=args.skills_path,
        model_id=args.model_id,
    )
    results = linker.link_and_group(
        text=args.text,
        threshold=args.threshold,
        top_k_candidates=args.top_k_candidates,
    )
    for item in results:
        mentions = ", ".join(item["mentions"])
        code = item.get("code") or "NA"
        print(f"{item['score']:.4f}\t{item['skill']}\t{code}\t[{mentions}]")


if __name__ == "__main__":
    main()
