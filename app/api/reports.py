from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.schemas.reports import TranscribeResponse, Transcript, TranscriptSegment
from app.services.transcription import transcribe_audio, TranscriptionError, assign_speakers_alternate
import traceback
router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_endpoint(
    file: UploadFile = File(...),
    language_hint: str | None = Query(default=None, description="ex: 'fr', 'en'"),
    diarization: str = Query(
        default="none",
        pattern="^(none|alternate)$",
        description="none=pas de speaker; alternate=alternance simple selon pauses"
    ),
    gap_threshold: float = Query(default=1.0, ge=0.2, le=5.0, description="seuil de pause (s) pour alternance"),
):
    """
    Transcrit l'audio en texte + segments.
    - language_hint: suggestion de langue (facultatif), la détection auto reste active côté modèle.
    - diarization='alternate': assigne 'Speaker 1/2' en alternant quand il y a une pause > gap_threshold.
    """
    try:
        content = await file.read()
        text, segs, lang = await transcribe_audio(content, file.filename, language_hint)
        if diarization == "alternate":
            segs = assign_speakers_alternate(segs, gap_threshold=gap_threshold, max_speakers=2)

        transcript = Transcript(
            language=lang or "unknown",
            text=text or "",
            segments=[TranscriptSegment(**s) for s in segs]
        )
        return TranscribeResponse(transcript=transcript)

    except TranscriptionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("TRACE:\n", traceback.format_exc(), flush=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
