import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import Settings
from .db import Database
from .models import (
    ChatRequest,
    ChatResponse,
    DecisionRecord,
    EngineeringDecisionFingerprint,
    Expert,
    ExpertCreate,
    IngestionResult,
    Source,
    WarRoomRequest,
    WarRoomResponse,
)
from .providers import (
    AzureOpenAIAnswerer,
    AzureOpenAIDecisionExtractor,
    AzureSpeechTranscriber,
    DecisionExtractor,
    HeuristicDecisionExtractor,
    LocalUnavailableTranscriber,
    Transcriber,
)
from .services import ChatService, FingerprintService, IngestionService, RetrievalService
from .war_room import (
    AzureOpenAIWarRoomOrchestrator,
    WarRoomGenerationError,
    WarRoomOrchestrator,
    WarRoomRosterError,
    WarRoomService,
    WarRoomUnavailableError,
    WarRoomValidationError,
)

BASE_DIR = Path(__file__).resolve().parent
ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".pptx",
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


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name[:180] or "upload"


def _build_extractor(settings: Settings) -> DecisionExtractor:
    if settings.extractor_provider == "heuristic":
        return HeuristicDecisionExtractor()
    if settings.extractor_provider == "azure-openai":
        return AzureOpenAIDecisionExtractor(settings)
    raise ValueError("EXTRACTOR_PROVIDER must be 'heuristic' or 'azure-openai'.")


def _build_transcriber(settings: Settings) -> Transcriber:
    if settings.transcription_provider == "local":
        return LocalUnavailableTranscriber()
    if settings.transcription_provider == "azure-speech":
        return AzureSpeechTranscriber(settings)
    raise ValueError("TRANSCRIPTION_PROVIDER must be 'local' or 'azure-speech'.")


def create_app(
    settings: Settings | None = None,
    extractor: DecisionExtractor | None = None,
    transcriber: Transcriber | None = None,
    answerer: AzureOpenAIAnswerer | None = None,
    war_room_orchestrator: WarRoomOrchestrator | None = None,
) -> FastAPI:
    settings = settings or Settings()
    settings.prepare()
    database = Database(settings.database_path)
    database.initialize()
    extractor = extractor or _build_extractor(settings)
    transcriber = transcriber or _build_transcriber(settings)
    if answerer is None and settings.chat_provider == "azure-openai":
        answerer = AzureOpenAIAnswerer(settings)
    elif settings.chat_provider not in {"local", "azure-openai"}:
        raise ValueError("CHAT_PROVIDER must be 'local' or 'azure-openai'.")
    if war_room_orchestrator is None and settings.war_room_provider == "azure-openai":
        war_room_orchestrator = AzureOpenAIWarRoomOrchestrator(settings)
    elif settings.war_room_provider not in {"disabled", "azure-openai"}:
        raise ValueError("WAR_ROOM_PROVIDER must be 'disabled' or 'azure-openai'.")

    ingestion = IngestionService(database, extractor, transcriber)
    fingerprints = FingerprintService(database)
    retrieval = RetrievalService(database)
    chat = ChatService(retrieval, fingerprints, answerer)
    war_room = WarRoomService(
        database,
        retrieval,
        war_room_orchestrator,
        settings.war_room_prompt_budget,
    )
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        database.initialize()
        if settings.seed_role_simulations:
            from .role_simulations import seed

            seed(settings.database_path, settings.role_simulations_corpus_dir)
        yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Evidence-grounded simulation of an expert's engineering judgment.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database
    app.state.war_room = war_room
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index(request: Request):
        return templates.TemplateResponse(request=request, name="index.html")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": settings.chat_provider}

    @app.post("/api/experts", response_model=Expert, status_code=201)
    def create_expert(payload: ExpertCreate) -> Expert:
        return database.create_expert(payload.name, payload.description)

    @app.get("/api/experts", response_model=list[Expert])
    def list_experts() -> list[Expert]:
        return database.list_experts()

    @app.get("/api/experts/{expert_id}", response_model=Expert)
    def get_expert(expert_id: str) -> Expert:
        expert = database.get_expert(expert_id)
        if not expert:
            raise HTTPException(status_code=404, detail="Expert not found.")
        return expert

    @app.post("/api/experts/{expert_id}/sources", response_model=IngestionResult, status_code=201)
    async def upload_source(
        expert_id: str,
        file: Annotated[UploadFile, File()],
        title: Annotated[str, Form()] = "",
        source_type: Annotated[str, Form()] = "auto",
    ) -> IngestionResult:
        if not database.get_expert(expert_id):
            raise HTTPException(status_code=404, detail="Expert not found.")
        original_name = _safe_filename(file.filename or "upload")
        extension = Path(original_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"Unsupported file type '{extension}'. Allowed: "
                    f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
                ),
            )
        if source_type not in {"auto", "document", "meeting-recording", "meeting-transcript"}:
            raise HTTPException(status_code=422, detail="Invalid source_type.")
        destination = settings.uploads_dir / f"{uuid.uuid4()}-{original_name}"
        max_bytes = settings.max_upload_mb * 1024 * 1024
        size = 0
        try:
            with destination.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Upload exceeds the {settings.max_upload_mb} MB limit.",
                        )
                    output.write(chunk)
        except HTTPException:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
        try:
            return ingestion.ingest(
                expert_id, destination, title or Path(original_name).stem, source_type
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, RuntimeError, ImportError, OSError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/experts/{expert_id}/sources", response_model=list[Source])
    def list_sources(expert_id: str) -> list[Source]:
        if not database.get_expert(expert_id):
            raise HTTPException(status_code=404, detail="Expert not found.")
        return database.list_sources(expert_id)

    @app.get("/api/experts/{expert_id}/decisions", response_model=list[DecisionRecord])
    def list_decisions(expert_id: str) -> list[DecisionRecord]:
        if not database.get_expert(expert_id):
            raise HTTPException(status_code=404, detail="Expert not found.")
        return database.list_decisions(expert_id)

    @app.get(
        "/api/experts/{expert_id}/fingerprint",
        response_model=EngineeringDecisionFingerprint,
    )
    def get_fingerprint(expert_id: str) -> EngineeringDecisionFingerprint:
        try:
            return fingerprints.derive(expert_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/experts/{expert_id}/chat", response_model=ChatResponse)
    def ask(expert_id: str, payload: ChatRequest) -> ChatResponse:
        try:
            return chat.answer(expert_id, payload.question, payload.top_k)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/war-room", response_model=WarRoomResponse)
    def run_war_room(payload: WarRoomRequest) -> WarRoomResponse:
        try:
            return war_room.run(payload.topic)
        except WarRoomRosterError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except WarRoomUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (WarRoomGenerationError, WarRoomValidationError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return app


app = create_app()
