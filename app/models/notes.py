# app/models/notes.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class Topic(BaseModel):
    title: str
    start: Optional[str] = None  # "HH:MM:SS" si disponible
    end: Optional[str] = None


class ActionItem(BaseModel):
    owner: Optional[str] = None
    action: str
    due: Optional[str] = None  # ISO date si détectée


class DecisionItem(BaseModel):
    decision: str
    due: Optional[str] = None  # ISO date si détectée


class MeetingSummary(BaseModel):
    executive_summary: str = Field(..., description="Résumé clair et concis")
    topics: List[Topic] = []
    decisions: List[DecisionItem] = []
    actions: List[ActionItem] = []


class NotesResponse(BaseModel):
    report_id: str
    language: str
    transcript_text: str
    summary: MeetingSummary
    exports: Dict[str, Optional[str]]
