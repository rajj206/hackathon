import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from .db import Database
from .models import (
    ChatResponse,
    Citation,
    DecisionRecord,
    EngineeringDecisionFingerprint,
    ExpertFinderResponse,
    ExpertMatch,
    FingerprintPattern,
    IngestionResult,
)
from .parsers import parse_file
from .providers import AzureOpenAIAnswerer, DecisionExtractor, Transcriber

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.-]{1,}", re.IGNORECASE)
AUDIO_VIDEO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
}
STOP_WORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "were",
    "have",
    "has",
    "our",
    "but",
    "not",
    "are",
    "was",
    "use",
    "used",
    "into",
    "because",
    "when",
    "then",
    "than",
    "they",
    "its",
}


def tokens(text: str) -> list[str]:
    found = [term.lower() for term in TOKEN_RE.findall(text)]
    expanded = [
        part
        for term in found
        for part in (term, *re.split(r"[-.]", term))
        if part and part not in STOP_WORDS
    ]
    return expanded


def is_expert_attributed(decision: DecisionRecord, expert_name: str) -> bool:
    return bool(
        decision.evidence_author
        and decision.evidence_author.strip().casefold() == expert_name.strip().casefold()
    )


class IngestionService:
    def __init__(self, db: Database, extractor: DecisionExtractor, transcriber: Transcriber):
        self.db = db
        self.extractor = extractor
        self.transcriber = transcriber

    def ingest(
        self, expert_id: str, path: Path, title: str, source_type: str = "auto"
    ) -> IngestionResult:
        expert = self.db.get_expert(expert_id)
        if not expert:
            raise LookupError("Expert not found.")
        effective_type = source_type
        if effective_type == "auto":
            effective_type = (
                "meeting-recording" if path.suffix.lower() in AUDIO_VIDEO_EXTENSIONS else "document"
            )
        source = self.db.create_source(expert_id, title or path.stem, path.name, effective_type)
        try:
            if (
                effective_type == "meeting-recording"
                or path.suffix.lower() in AUDIO_VIDEO_EXTENSIONS
            ):
                segments = self.transcriber.transcribe(path)
            else:
                segments = parse_file(path, reviewer_name=expert.name)
            if not segments:
                raise ValueError("No readable text was found in the uploaded source.")
            self.db.store_segments(source.id, segments)
            decisions = self.extractor.extract(
                expert.id, expert.name, source.id, source.title, segments
            )
            self.db.store_decisions(decisions)
            self.db.update_source(source.id, "ready")
            return IngestionResult(source=self.db.get_source(source.id), decisions=decisions)
        except (ValueError, RuntimeError, ImportError, OSError) as exc:
            self.db.update_source(source.id, "failed", str(exc))
            raise


def _patterns(
    category: str, items: list[tuple[str, str]], minimum: int = 1
) -> list[FingerprintPattern]:
    grouped: dict[str, list[str]] = defaultdict(list)
    display: dict[str, str] = {}
    for text, decision_id in items:
        normalized = re.sub(r"\s+", " ", text.strip().lower())[:180]
        if not normalized:
            continue
        grouped[normalized].append(decision_id)
        display.setdefault(normalized, text.strip()[:180])
    ranked = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    return [
        FingerprintPattern(
            category=category,
            pattern=display[key],
            support_count=len(ids),
            decision_ids=ids,
            confidence=min(0.45 + 0.14 * len(ids), 0.92),
        )
        for key, ids in ranked
        if len(ids) >= minimum
    ][:8]


class FingerprintService:
    def __init__(self, db: Database):
        self.db = db

    def derive(self, expert_id: str) -> EngineeringDecisionFingerprint:
        expert = self.db.get_expert(expert_id)
        if not expert:
            raise LookupError("Expert not found.")
        all_decisions = self.db.list_decisions(expert_id)
        simulated_decisions = [decision for decision in all_decisions if decision.simulation]
        eligible_decisions = simulated_decisions or all_decisions
        decisions = [
            decision
            for decision in eligible_decisions
            if is_expert_attributed(decision, expert.name)
        ]
        preferences = [(d.choice, d.id) for d in decisions]
        tradeoffs = [
            (f"{d.choice} instead of {alternative}", d.id)
            for d in decisions
            for alternative in d.alternatives
        ]
        risks = [(risk, d.id) for d in decisions for risk in d.risks]
        criteria = [(item, d.id) for d in decisions for item in (d.rationale + d.constraints)]
        troubleshooting = [
            (d.decision, d.id)
            for d in decisions
            if "troubleshooting" in d.tags
            or any(
                term in d.evidence_text.lower()
                for term in ("incident", "debug", "root cause", "diagnos")
            )
        ]
        operations = [
            (d.decision, d.id)
            for d in decisions
            if any(tag in d.tags for tag in ("operations", "reliability", "telemetry"))
        ]
        lessons = [(f"{d.choice}: {d.outcome}", d.id) for d in decisions if d.outcome]
        return EngineeringDecisionFingerprint(
            expert_id=expert.id,
            expert_name=expert.name,
            decision_count=len(decisions),
            total_decision_count=len(eligible_decisions),
            expert_attributed_decision_count=len(decisions),
            contextual_decision_count=len(eligible_decisions) - len(decisions),
            recurring_preferences=_patterns("recurring preference", preferences),
            tradeoffs=_patterns("tradeoff", tradeoffs),
            risk_posture=_patterns("risk posture", risks),
            technology_criteria=_patterns("technology criterion", criteria),
            troubleshooting_strategies=_patterns("troubleshooting strategy", troubleshooting),
            operational_practices=_patterns("operational practice", operations),
            outcome_backed_lessons=_patterns("outcome-backed lesson", lessons),
        )


def _rank_documents(
    documents: list[DecisionRecord], query: str, top_k: int
) -> list[tuple[DecisionRecord, float]]:
    if not documents:
        return []
    query_terms = tokens(query)
    if not query_terms:
        return []
    document_terms = [
        tokens(
            " ".join(
                [
                    d.decision,
                    d.choice,
                    " ".join(d.alternatives),
                    " ".join(d.rationale),
                    " ".join(d.constraints),
                    " ".join(d.risks),
                    d.outcome or "",
                    d.evidence_text,
                    " ".join(d.tags),
                ]
            )
        )
        for d in documents
    ]
    document_frequency = Counter(term for terms in document_terms for term in set(terms))
    count = len(documents)

    def vector(terms: list[str]) -> dict[str, float]:
        frequencies = Counter(terms)
        return {
            term: frequency * (math.log((count + 1) / (document_frequency.get(term, 0) + 1)) + 1)
            for term, frequency in frequencies.items()
        }

    query_vector = vector(query_terms)
    scored = []
    for decision, terms in zip(documents, document_terms, strict=True):
        doc_vector = vector(terms)
        dot = sum(query_vector.get(term, 0) * doc_vector.get(term, 0) for term in query_vector)
        norm_q = math.sqrt(sum(value * value for value in query_vector.values()))
        norm_d = math.sqrt(sum(value * value for value in doc_vector.values()))
        semantic = dot / (norm_q * norm_d) if norm_q and norm_d else 0
        lexical = len(set(query_terms) & set(terms)) / len(set(query_terms))
        phrase_bonus = 0.15 if query.lower() in decision.evidence_text.lower() else 0
        score = 0.6 * semantic + 0.4 * lexical + phrase_bonus
        if score > 0:
            scored.append((decision, score))
    return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


class RetrievalService:
    def __init__(self, db: Database):
        self.db = db

    def search(
        self, expert_id: str, query: str, top_k: int = 5
    ) -> list[tuple[DecisionRecord, float]]:
        documents = self.db.list_decisions(expert_id)
        simulated_documents = [decision for decision in documents if decision.simulation]
        documents = simulated_documents or documents
        return _rank_documents(documents, query, top_k)


def _citation(decision: DecisionRecord, expert_name: str) -> Citation:
    return Citation(
        source_id=decision.source_id,
        source_title=decision.source_title,
        page_or_segment=decision.page_or_segment,
        decision_id=decision.id,
        excerpt=decision.evidence_text[:260],
        evidence_type=decision.evidence_type,
        evidence_author=decision.evidence_author,
        evidence_role=decision.evidence_role,
        comment_id=decision.comment_id,
        anchor_text=decision.anchor_text,
        parent_comment_id=decision.parent_comment_id,
        parent_author=decision.parent_author,
        attribution_status=(
            "expert_attributed" if is_expert_attributed(decision, expert_name) else "contextual"
        ),
        decision_confidence=decision.confidence,
        simulation=decision.simulation,
        simulation_namespace=decision.simulation_namespace,
    )


class ExpertFinderService:
    def __init__(self, db: Database):
        self.db = db

    def find(self, question: str, top_k: int = 5) -> ExpertFinderResponse:
        query_terms = set(tokens(question))
        ranked: list[tuple[float, ExpertMatch]] = []
        experts = self.db.list_experts()
        experts_by_id = {expert.id: expert for expert in experts}
        documents = []
        for expert in experts:
            expert_documents = self.db.list_decisions(expert.id)
            simulated = [decision for decision in expert_documents if decision.simulation]
            documents.extend(
                decision
                for decision in (simulated or expert_documents)
                if is_expert_attributed(decision, expert.name)
            )
        globally_ranked = _rank_documents(documents, question, len(documents))
        matches_by_expert: dict[str, list[tuple[DecisionRecord, float]]] = defaultdict(list)
        for item in globally_ranked:
            matches_by_expert[item[0].expert_id].append(item)

        for expert_id, matches in matches_by_expert.items():
            expert = experts_by_id[expert_id]
            matches = matches[:4]
            if not matches:
                continue
            evidence_terms = set(
                tokens(
                    " ".join(
                        " ".join(
                            (
                                decision.decision,
                                decision.choice,
                                decision.evidence_text,
                                " ".join(decision.tags),
                            )
                        )
                        for decision, _score in matches
                    )
                )
            )
            matched_terms = sorted(query_terms & evidence_terms)
            coverage = len(matched_terms) / max(len(query_terms), 1)
            top_score = matches[0][1]
            evidence_score = min(len(matches) / 3, 1)
            score = min(0.98, 0.55 * top_score + 0.25 * coverage + 0.20 * evidence_score)
            if score < 0.12:
                continue
            decisions = [decision for decision, _score in matches[:3]]
            projects = {
                decision.source_title.split(" — ", 1)[0]
                for decision in decisions
                if " — " in decision.source_title
            }
            terms_text = ", ".join(matched_terms[:6]) or "the requested engineering area"
            scope = (
                f"{len(projects)} project{'s' if len(projects) != 1 else ''}"
                if projects
                else f"{len(decisions)} evidence source{'s' if len(decisions) != 1 else ''}"
            )
            explanation = (
                f"{len(decisions)} attributed decisions across {scope} match {terms_text}."
            )
            ranked.append(
                (
                    score,
                    ExpertMatch(
                        expert_id=expert.id,
                        expert_name=expert.name,
                        role=expert.description,
                        score=round(score, 3),
                        confidence=(
                            "strong" if len(decisions) >= 2 and score >= 0.35 else "limited"
                        ),
                        evidence_count=len(decisions),
                        project_count=len(projects),
                        matched_terms=matched_terms[:8],
                        explanation=explanation,
                        citations=[_citation(decision, expert.name) for decision in decisions],
                    ),
                )
            )
        ranked.sort(key=lambda item: (-item[0], item[1].expert_name))
        return ExpertFinderResponse(
            question=question,
            matches=[match for _score, match in ranked[:top_k]],
        )


class ChatService:
    def __init__(
        self,
        retrieval: RetrievalService,
        fingerprints: FingerprintService,
        answerer: AzureOpenAIAnswerer | None = None,
    ):
        self.retrieval = retrieval
        self.fingerprints = fingerprints
        self.answerer = answerer

    def answer(self, expert_id: str, question: str, top_k: int = 5) -> ChatResponse:
        matches = self.retrieval.search(expert_id, question, top_k)
        fingerprint = self.fingerprints.derive(expert_id)
        expert_name = fingerprint.expert_name
        attributed_matches = [
            item for item in matches if is_expert_attributed(item[0], expert_name)
        ]
        contextual_match_count = len(matches) - len(attributed_matches)
        citations = [_citation(decision, expert_name) for decision, _score in matches]
        if not matches:
            return ChatResponse(
                answer=(
                    "## Evidence-backed view\n"
                    "No supplied decision record directly supports an answer.\n\n"
                    "## Inferred pattern\n"
                    "The fingerprint is not used to fill this evidence gap.\n\n"
                    "## Uncertainty\n"
                    "Insufficient evidence. Add a relevant design note, ADR, or meeting transcript."
                ),
                citations=[],
                evidence_strength="insufficient",
                expert_attributed_citation_count=0,
                contextual_citation_count=0,
            )

        strength = (
            "strong"
            if len(attributed_matches) >= 2 and attributed_matches[0][1] >= 0.35
            else "limited"
        )
        evidence_lines = []
        for index, (decision, _score) in enumerate(matches, start=1):
            rationale = "; ".join(decision.rationale) or "No explicit rationale extracted"
            attributed = is_expert_attributed(decision, expert_name)
            provenance = (
                f"EXPERT-ATTRIBUTED JUDGMENT by {decision.evidence_author}"
                if attributed
                else (
                    f"CONTEXTUAL ATTRIBUTED STATEMENT by {decision.evidence_author}; "
                    "not the selected expert's view"
                    if decision.evidence_author
                    else "CONTEXTUAL DOCUMENT CONTENT; author not established"
                )
            )
            evidence_lines.append(
                f"[{index}] {provenance}: {decision.choice}. Rationale: {rationale} "
                f"({decision.source_title}, {decision.page_or_segment})"
            )
        inferred_patterns = (
            fingerprint.recurring_preferences[:2]
            + fingerprint.tradeoffs[:2]
            + fingerprint.technology_criteria[:2]
        )
        fingerprint_text = (
            "\n".join(
                f"- {pattern.pattern} (support: {pattern.support_count})"
                for pattern in inferred_patterns
            )
            or "- No stable pattern has enough support yet."
        )
        evidence_text = "\n".join(evidence_lines)
        if self.answerer:
            answer = self.answerer.answer(question, evidence_text, fingerprint_text)
        else:
            answer = (
                f"## Evidence-backed view\n{evidence_text}\n\n"
                f"## Inferred fingerprint pattern\n{fingerprint_text}\n\n"
                "## Uncertainty\n"
                + (
                    "The supplied evidence contains multiple relevant records, but this remains "
                    "a simulation and may omit current constraints."
                    if strength == "strong"
                    else (
                        "Evidence is limited to a small or weakly matching set of records; "
                        "treat this as a hypothesis."
                    )
                )
            )
        return ChatResponse(
            answer=answer,
            citations=citations,
            evidence_strength=strength,
            expert_attributed_citation_count=len(attributed_matches),
            contextual_citation_count=contextual_match_count,
        )
