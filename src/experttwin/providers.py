import json
import re
import shutil
import subprocess
import threading
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from .config import Settings
from .models import DecisionRecord, ParsedSegment


class ProviderConfigurationError(RuntimeError):
    pass


class TranscriptionError(RuntimeError):
    pass


class DecisionExtractor(ABC):
    @abstractmethod
    def extract(
        self,
        expert_id: str,
        expert_name: str,
        source_id: str,
        source_title: str,
        segments: list[ParsedSegment],
    ) -> list[DecisionRecord]:
        raise NotImplementedError


class Transcriber(ABC):
    @abstractmethod
    def transcribe(self, path: Path) -> list[ParsedSegment]:
        raise NotImplementedError


DECISION_MARKERS = re.compile(
    r"\b(chose|choose|selected|use|used|prefer|preferred|recommend|adopted|migrated|"
    r"standardized|decided|instead of|rather than| over | versus | vs\.?)\b",
    re.IGNORECASE,
)
COMMENT_JUDGMENT_MARKERS = re.compile(
    r"\b(recommend\w*|suggest\w*|should|must|object\w*|concern\w*|approv\w*|"
    r"accept\w*|reject\w*|agree\w*|yes|resolv\w*|address\w*|answer\w*|"
    r"acknowledg\w*|refin\w*|risk\w*|change\w*|avoid\w*|clarif\w*|"
    r"consider\w*|prefer\w*)\b",
    re.IGNORECASE,
)
RATIONALE_MARKERS = re.compile(
    r"\b(because|due to|so that|in order to|given that)\b", re.IGNORECASE
)
RISK_MARKERS = re.compile(
    r"\b(risk|failure|outage|latency|cost|lock-in|security|privacy|downtime|bottleneck)\b",
    re.IGNORECASE,
)
CONSTRAINT_MARKERS = re.compile(
    r"\b(constraint|budget|deadline|scale|throughput|compliance|legacy|limited|must|require)\b",
    re.IGNORECASE,
)
OUTCOME_MARKERS = re.compile(
    r"\b(result|outcome|reduced|improved|increased|decreased|saved|failed|worked)\b",
    re.IGNORECASE,
)
TAG_TERMS = {
    "azure": "azure",
    "data explorer": "azure-data-explorer",
    "kusto": "kusto",
    "synapse": "synapse",
    "sql": "sql",
    "telemetry": "telemetry",
    "monitoring": "operations",
    "incident": "troubleshooting",
    "debug": "troubleshooting",
    "reliability": "reliability",
    "security": "security",
    "cost": "cost",
    "latency": "performance",
    "scale": "scalability",
    "container": "containers",
}


def _sentences(text: str, min_length: int = 20) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
        if len(sentence.strip()) >= min_length
    ]


def _clip(text: str, length: int = 700) -> str:
    return text.strip()[:length]


def _segment_evidence(segment: ParsedSegment) -> str:
    if segment.comment_id is None:
        if segment.author:
            role = f" ({segment.speaker_role})" if segment.speaker_role else ""
            return (
                f"Attributed transcript statement by {segment.author}{role}: "
                f"{_clip(segment.text)}"
            )
        return _clip(segment.text)
    if segment.parent_comment_id:
        evidence = (
            f"Parent review comment by {segment.parent_author or 'unknown reviewer'}: "
            f"{_clip(segment.parent_text or 'Unavailable', 400)}\n"
            f"Selected expert reply by {segment.author or 'selected expert'}: "
            f"{_clip(segment.text, 700)}"
        )
    else:
        evidence = f"Review comment: {_clip(segment.text, 700)}"
    if segment.anchor_text:
        evidence += f"\nAnchored document context: {_clip(segment.anchor_text, 450)}"
    return evidence


def _evidence_type(segment: ParsedSegment) -> str:
    if segment.comment_id is not None:
        return "review_comment"
    if segment.author:
        return "transcript_turn"
    return "document"


class HeuristicDecisionExtractor(DecisionExtractor):
    def extract(
        self,
        expert_id: str,
        expert_name: str,
        source_id: str,
        source_title: str,
        segments: list[ParsedSegment],
    ) -> list[DecisionRecord]:
        records: list[DecisionRecord] = []
        for segment in segments:
            sentences = _sentences(segment.text, min_length=3 if segment.comment_id else 20)
            candidates = [
                sentence
                for sentence in sentences
                if DECISION_MARKERS.search(sentence)
                or (
                    segment.comment_id is not None
                    and COMMENT_JUDGMENT_MARKERS.search(sentence)
                )
            ]
            for sentence in candidates[:4]:
                rationale = []
                if match := RATIONALE_MARKERS.search(sentence):
                    rationale.append(_clip(sentence[match.end() :].strip(" ,:;")))
                alternatives = []
                alternative_match = re.search(
                    r"\b(?:over|instead of|rather than|versus|vs\.?)\s+([^.;]+)",
                    sentence,
                    re.IGNORECASE,
                )
                if alternative_match:
                    alternatives.append(_clip(alternative_match.group(1), 180))
                constraints = [s for s in sentences if CONSTRAINT_MARKERS.search(s)][:2]
                risks = [s for s in sentences if RISK_MARKERS.search(s) and s != sentence][:2]
                outcomes = [s for s in sentences if OUTCOME_MARKERS.search(s) and s != sentence]
                lower_text = segment.text.lower()
                tags = sorted({tag for term, tag in TAG_TERMS.items() if term in lower_text})
                confidence = 0.58
                if rationale:
                    confidence += 0.12
                if alternatives:
                    confidence += 0.08
                if outcomes:
                    confidence += 0.07
                records.append(
                    DecisionRecord(
                        id=str(uuid.uuid4()),
                        expert_id=expert_id,
                        expert=expert_name,
                        decision=_clip(sentence, 300),
                        choice=_clip(
                            re.split(r"\b(?:because|due to|so that)\b", sentence, flags=re.I)[0],
                            220,
                        ),
                        alternatives=alternatives,
                        rationale=rationale,
                        constraints=[_clip(item, 300) for item in constraints],
                        risks=[_clip(item, 300) for item in risks],
                        outcome=_clip(outcomes[0], 350) if outcomes else None,
                        source_id=source_id,
                        source_title=source_title,
                        evidence_text=_segment_evidence(segment),
                        page_or_segment=segment.page_or_segment,
                        evidence_type=_evidence_type(segment),
                        evidence_author=segment.author,
                        evidence_role=segment.speaker_role,
                        comment_id=segment.comment_id,
                        anchor_text=segment.anchor_text,
                        parent_comment_id=segment.parent_comment_id,
                        parent_author=segment.parent_author,
                        parent_text=segment.parent_text,
                        timestamp=segment.timestamp,
                        tags=tags,
                        confidence=min(confidence, 0.9),
                    )
                )
        return records


class AzureOpenAIDecisionExtractor(DecisionExtractor):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = _azure_openai_client(settings)

    def extract(
        self,
        expert_id: str,
        expert_name: str,
        source_id: str,
        source_title: str,
        segments: list[ParsedSegment],
    ) -> list[DecisionRecord]:
        results: list[DecisionRecord] = []
        for segment in segments:
            if segment.comment_id is not None:
                thread_context = (
                    f"""
Evidence type: threaded review reply
Parent comment ID: {segment.parent_comment_id}
Parent reviewer: {segment.parent_author or "Unknown"}
Parent comment (context only; do not attribute this reviewer's view to the selected expert):
{(segment.parent_text or "Unavailable")[:10000]}
Selected expert reply:
{segment.text[:10000]}
""".strip()
                    if segment.parent_comment_id
                    else f"""
Evidence type: review comment
Comment text:
{segment.text[:10000]}
""".strip()
                )
                prompt = f"""
Extract engineering judgment from the supplied review comment. Return a JSON object with
a "decisions" array. Each item must contain: decision, choice, alternatives (array),
rationale (array), constraints (array), risks (array), outcome (string or null), tags
(array), confidence (0..1).

Treat recommendations, objections, approvals, risk concerns, suggested changes,
acceptance, rejection, refinement, answers, risk-gap acknowledgment, and explicit
rationale as engineering judgment signals, including terse comments. For a threaded
reply, extract only the selected expert's judgment from the reply; the parent comment is
context and must not be attributed to the selected expert. Use anchored document context
only to understand what the review refers to. Do not invent facts, decisions, rationale,
outcomes, or reviewer intent. Return an empty array only when the selected expert's
comment or reply contains no engineering judgment.

Reviewer: {segment.author or expert_name}
Selected expert: {expert_name}
Comment ID: {segment.comment_id}
Comment location: {segment.page_or_segment}
{thread_context}
Anchored document context:
{(segment.anchor_text or "Unavailable")[:10000]}
""".strip()
            elif segment.author:
                role = f" ({segment.speaker_role})" if segment.speaker_role else ""
                prompt = f"""
Extract engineering decisions or judgment from this attributed transcript turn. Return a
JSON object with a "decisions" array. Each item must contain: decision, choice,
alternatives (array), rationale (array), constraints (array), risks (array), outcome
(string or null), tags (array), confidence (0..1).

Evidence type: attributed transcript turn
Speaker: {segment.author}{role}
Selected expert: {expert_name}
Timestamp: {segment.timestamp or "Unavailable"}
Turn location: {segment.page_or_segment}
Turn text:
{segment.text[:10000]}

Attribute statements only to the named speaker. A non-selected speaker is contextual
evidence and must not be presented as the selected expert's judgment. Treat explicit
recommendations, decisions, objections, approvals, refinements, constraints, risks, and
measured outcomes as judgment signals. Do not invent facts or intent. Return an empty
array when the turn contains no engineering judgment.
""".strip()
            else:
                prompt = f"""
Extract engineering decisions from the supplied evidence. Return a JSON object with a
"decisions" array. Each item must contain: decision, choice, alternatives (array),
rationale (array), constraints (array), risks (array), outcome (string or null), tags
(array), confidence (0..1). Do not invent facts. Return an empty array if no engineering
choice is evidenced.

Evidence location: {segment.page_or_segment}
Evidence:
{segment.text[:10000]}
""".strip()
            response = self.client.chat.completions.create(
                model=self.settings.azure_openai_chat_deployment,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You extract auditable engineering decision records.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            payload = json.loads(response.choices[0].message.content or '{"decisions":[]}')
            for item in payload.get("decisions", []):
                results.append(
                    DecisionRecord(
                        id=str(uuid.uuid4()),
                        expert_id=expert_id,
                        expert=expert_name,
                        source_id=source_id,
                        source_title=source_title,
                        evidence_text=_segment_evidence(segment),
                        page_or_segment=segment.page_or_segment,
                        evidence_type=_evidence_type(segment),
                        evidence_author=segment.author,
                        evidence_role=segment.speaker_role,
                        comment_id=segment.comment_id,
                        anchor_text=segment.anchor_text,
                        parent_comment_id=segment.parent_comment_id,
                        parent_author=segment.parent_author,
                        parent_text=segment.parent_text,
                        timestamp=segment.timestamp,
                        **item,
                    )
                )
        return results


class LocalUnavailableTranscriber(Transcriber):
    def transcribe(self, path: Path) -> list[ParsedSegment]:
        raise TranscriptionError(
            "Local audio/video transcription is not installed because it requires heavyweight "
            "speech models. Upload a TXT transcript, or set TRANSCRIPTION_PROVIDER=azure-speech "
            "with AZURE_SPEECH_KEY and AZURE_SPEECH_REGION. For video and compressed audio, "
            "install ffmpeg and ensure it is on PATH."
        )


class AzureSpeechTranscriber(Transcriber):
    def __init__(self, settings: Settings):
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise ProviderConfigurationError(
                "Azure Speech transcription requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION. "
                "The Speech SDK file adapter used here does not support passwordless "
                "authentication."
            )
        self.settings = settings

    def transcribe(self, path: Path) -> list[ParsedSegment]:
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError as exc:
            raise ProviderConfigurationError(
                "Install the Azure extras with: pip install -e '.[azure]'"
            ) from exc

        audio_path = self._ensure_wav(path)
        speech_config = speechsdk.SpeechConfig(
            subscription=self.settings.azure_speech_key,
            region=self.settings.azure_speech_region,
        )
        speech_config.speech_recognition_language = self.settings.azure_speech_language
        audio_config = speechsdk.audio.AudioConfig(filename=str(audio_path))
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )
        completed = threading.Event()
        segments: list[ParsedSegment] = []
        errors: list[str] = []

        def recognized(event) -> None:
            result = event.result
            if result.reason == speechsdk.ResultReason.RecognizedSpeech and result.text.strip():
                offset_seconds = getattr(result, "offset", 0) / 10_000_000
                segments.append(
                    ParsedSegment(
                        text=result.text.strip(),
                        page_or_segment=f"audio segment {len(segments) + 1}",
                        timestamp=f"{offset_seconds:.1f}s",
                    )
                )

        def canceled(event) -> None:
            errors.append(str(event))
            completed.set()

        recognizer.recognized.connect(recognized)
        recognizer.session_stopped.connect(lambda _event: completed.set())
        recognizer.canceled.connect(canceled)
        recognizer.start_continuous_recognition()
        if not completed.wait(timeout=3600):
            recognizer.stop_continuous_recognition()
            raise TranscriptionError("Azure Speech transcription timed out after one hour.")
        recognizer.stop_continuous_recognition()
        if errors:
            raise TranscriptionError(f"Azure Speech transcription failed: {errors[0]}")
        if not segments:
            raise TranscriptionError("Azure Speech returned no recognized speech.")
        return segments

    @staticmethod
    def _ensure_wav(path: Path) -> Path:
        if path.suffix.lower() == ".wav":
            return path
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise TranscriptionError(
                "ffmpeg is required to convert this audio/video file to WAV. Install ffmpeg "
                "and ensure it is on PATH, or upload a WAV file/TXT transcript."
            )
        converted = path.with_suffix(".speech.wav")
        process = subprocess.run(
            [ffmpeg, "-y", "-i", str(path), "-ac", "1", "-ar", "16000", str(converted)],
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        if process.returncode != 0:
            raise TranscriptionError(f"ffmpeg conversion failed: {process.stderr[-500:]}")
        return converted


def _azure_openai_client(settings: Settings):
    if not settings.azure_openai_endpoint or not settings.azure_openai_chat_deployment:
        raise ProviderConfigurationError(
            "Azure OpenAI requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_CHAT_DEPLOYMENT."
        )
    try:
        from openai import AzureOpenAI
    except ImportError as exc:
        raise ProviderConfigurationError(
            "Install Azure extras with: pip install -e '.[azure]'"
        ) from exc

    if settings.azure_openai_api_key:
        return AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
    try:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    except ImportError as exc:
        raise ProviderConfigurationError(
            "Install Azure extras with: pip install -e '.[azure]'"
        ) from exc
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_ad_token_provider=token_provider,
        api_version=settings.azure_openai_api_version,
    )


class AzureOpenAIAnswerer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = _azure_openai_client(settings)

    def answer(self, question: str, evidence: str, fingerprint: str) -> str:
        response = self.client.chat.completions.create(
            model=self.settings.azure_openai_chat_deployment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an engineering-judgment simulation based only on supplied work "
                        "history. Distinguish EXPERT-ATTRIBUTED JUDGMENT from CONTEXTUAL "
                        "DOCUMENT CONTENT. Never claim contextual content is the expert's view "
                        "when its author is not established. Separate source-backed facts from "
                        "inferred fingerprint patterns. "
                        "Use citation labels exactly as provided. State uncertainty and never "
                        "claim to be the real expert."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\nSOURCE EVIDENCE:\n{evidence}\n\n"
                        f"INFERRED FINGERPRINT:\n{fingerprint}\n\n"
                        "Answer with headings: Evidence-backed view, Inferred pattern, Uncertainty."
                    ),
                },
            ],
        )
        return response.choices[0].message.content or "Insufficient evidence to answer."
