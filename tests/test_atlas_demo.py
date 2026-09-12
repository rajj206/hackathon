from pathlib import Path

from experttwin.parsers import parse_file

ROOT = Path("demo-data/atlas-audit")
TEXT_ARTIFACTS = [
    "README.md",
    "02-design-challenge-chat.txt",
    "03-architecture-review-transcript.txt",
    "04-audio-recording-script.txt",
    "05-incident-report.md",
    "06-revised-adr.md",
    "07-three-month-outcome.md",
]
REQUIRED_ARTIFACTS = [
    "01-initial-design-review.docx",
    *TEXT_ARTIFACTS,
    "04-architecture-review.wav",
]


def test_atlas_demo_has_required_synthetic_artifacts():
    assert all((ROOT / name).is_file() for name in REQUIRED_ARTIFACTS)
    for name in TEXT_ARTIFACTS:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "SYNTHETIC FICTIONAL HACKATHON DATA" in text

    document_segments = parse_file(ROOT / "01-initial-design-review.docx")
    body_text = "\n".join(
        segment.text for segment in document_segments if segment.comment_id is None
    )
    assert "SYNTHETIC FICTIONAL HACKATHON DATA" in body_text

    wav = (ROOT / "04-architecture-review.wav").read_bytes()
    assert len(wav) > 44
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"


def test_atlas_docx_threads_and_maya_attribution():
    all_segments = parse_file(ROOT / "01-initial-design-review.docx")
    all_comments = [segment for segment in all_segments if segment.comment_id]
    maya_segments = parse_file(
        ROOT / "01-initial-design-review.docx",
        reviewer_name="maya rao",
    )
    maya_comments = [segment for segment in maya_segments if segment.comment_id]

    assert len(all_comments) == 10
    assert sum(comment.parent_comment_id is None for comment in all_comments) == 5
    assert sum(comment.parent_comment_id is not None for comment in all_comments) == 5
    assert len(maya_comments) == 5
    assert all(comment.author == "Maya Rao" for comment in maya_comments)
    assert all(comment.parent_comment_id for comment in maya_comments)
    assert all(comment.parent_author for comment in maya_comments)
    assert all(comment.parent_text for comment in maya_comments)
    assert all(comment.anchor_text for comment in maya_comments)
    assert all("reply to comment" in comment.page_or_segment for comment in maya_comments)


def test_atlas_narrative_is_consistent_and_compact():
    chronology = [
        "01-initial-design-review.docx",
        "02-design-challenge-chat.txt",
        "03-architecture-review-transcript.txt",
        "05-incident-report.md",
        "06-revised-adr.md",
        "07-three-month-outcome.md",
    ]
    segments = []
    for name in chronology:
        segments.extend(parse_file(ROOT / name, reviewer_name="Maya Rao"))
    corpus = "\n".join(segment.text for segment in segments).lower()

    assert 20 <= len(segments) <= 30
    assert sum(segment.comment_id is not None for segment in segments) == 5
    assert sum(
        bool(segment.author and segment.author.casefold() == "maya rao")
        for segment in segments
    ) == 11
    assert "80,000" in corpus
    assert "14-day hot retention" in corpus
    assert "47 minutes" in corpus
    assert "37% below" in corpus
    assert "2.8 seconds p95" in corpus
    assert "synchronous dual-write" in corpus
    assert "synapse serverless" in corpus
    assert "hash-chain" in corpus
