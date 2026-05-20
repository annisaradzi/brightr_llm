"""Pydantic DTOs for inspection session API."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

RustGrade = Literal["Ri1", "Ri2", "R3", "R4", "R5"]
RecommendationCode = Literal["TBR", "TBRy", "TBP", "TBM", "TBS"]
Priority = Literal["low", "medium", "high"]
EquipmentType = Literal["piping", "pressure_vessel", "flange", "structural", "other"]
ReviewStatus = Literal["unreviewed", "in_progress", "confirmed"]
SessionStatus = Literal["draft", "submitted", "in_review", "approved"]
AnalysisStatus = Literal["pending", "complete", "failed"]


class BoundingBoxOut(BaseModel):
    label: str
    x: float
    y: float
    w: float
    h: float
    confidence: Optional[float] = None


class CreateSessionRequest(BaseModel):
    createdBy: Optional[str] = None


class SubmitSessionRequest(BaseModel):
    userReportNumber: Optional[str] = None
    plant: Optional[str] = None
    systemCode: Optional[str] = None
    preparerName: Optional[str] = None
    reviewerName: Optional[str] = None
    approverName: Optional[str] = None


class InspectionItemPatch(BaseModel):
    findings: Optional[str] = None
    recommendation: Optional[str] = None
    rustGrade: Optional[RustGrade] = None
    cof: Optional[int] = Field(None, ge=1, le=5)
    findingsPriority: Optional[Priority] = None
    sapPriority: Optional[Priority] = None
    equipmentType: Optional[EquipmentType] = None
    equipmentId: Optional[str] = None
    recommendationCode: Optional[RecommendationCode] = None
    furtherInspection: Optional[bool] = None
    openInsulation: Optional[bool] = None
    scaffold: Optional[bool] = None
    reviewStatus: Optional[ReviewStatus] = None

    @field_validator("cof")
    @classmethod
    def cof_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 5):
            raise ValueError("cof must be between 1 and 5")
        return v


class InspectionItemOut(BaseModel):
    id: str
    code: str
    sessionId: str
    sortOrder: int
    imageUrl: str
    imageWidth: Optional[int] = None
    imageHeight: Optional[int] = None
    aiFindings: Optional[str] = None
    aiRecommendation: Optional[str] = None
    aiBoundingBoxes: List[BoundingBoxOut] = Field(default_factory=list)
    aiConfidence: Optional[float] = None
    aiAnalyzedAt: Optional[datetime] = None
    findings: Optional[str] = None
    recommendation: Optional[str] = None
    rustGrade: Optional[str] = None
    cof: Optional[int] = None
    findingsPriority: Optional[str] = None
    sapPriority: Optional[str] = None
    equipmentType: Optional[str] = None
    equipmentId: Optional[str] = None
    recommendationCode: Optional[str] = None
    furtherInspection: bool = False
    openInsulation: bool = False
    scaffold: bool = False
    reviewStatus: str = "unreviewed"
    analysisStatus: str = "pending"
    analysisError: Optional[str] = None
    editedFields: List[str] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class InspectionSessionOut(BaseModel):
    id: str
    status: str
    createdBy: str
    systemReportNumber: Optional[str] = None
    userReportNumber: Optional[str] = None
    plant: Optional[str] = None
    systemCode: Optional[str] = None
    preparerName: Optional[str] = None
    reviewerName: Optional[str] = None
    approverName: Optional[str] = None
    executiveSummary: Optional[str] = None
    pdfUrl: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    submittedAt: Optional[datetime] = None
    items: List[InspectionItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class UploadImagesResponse(BaseModel):
    sessionId: str
    items: List[InspectionItemOut]


class ReportSummaryOut(BaseModel):
    id: str
    systemReportNumber: str
    userReportNumber: Optional[str] = None
    plant: Optional[str] = None
    systemCode: Optional[str] = None
    preparerName: Optional[str] = None
    reviewerName: Optional[str] = None
    approverName: Optional[str] = None
    equipmentType: Optional[str] = None
    equipmentId: Optional[str] = None
    status: SessionStatus | str
    submittedAt: Optional[datetime] = None
    totalFindings: int = 0
    highPriorityCount: int = 0
    tbsCount: int = 0
    avgCof: Optional[float] = None


class ReportListResponse(BaseModel):
    reports: List[ReportSummaryOut]
    total: int
    page: int
    limit: int


class ReportDetailOut(ReportSummaryOut):
    executiveSummary: Optional[str] = None
    createdBy: str
    createdAt: datetime
    updatedAt: datetime
    pdfUrl: Optional[str] = None
    reviewedAt: Optional[datetime] = None
    approvedAt: Optional[datetime] = None
    reviewComment: Optional[str] = None
    items: List[InspectionItemOut] = Field(default_factory=list)


class RequestChangesBody(BaseModel):
    comment: str = Field(..., min_length=1)


class ReportActionOut(BaseModel):
    id: str
    status: str
    message: str
