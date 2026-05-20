export type RustGrade = "Ri1" | "Ri2" | "R3" | "R4" | "R5";
export type RecommendationCode = "TBR" | "TBRy" | "TBP" | "TBM" | "TBS";
export type Priority = "low" | "medium" | "high";
export type EquipmentType =
  | "piping"
  | "pressure_vessel"
  | "flange"
  | "structural"
  | "other";
export type ReviewStatus = "unreviewed" | "in_progress" | "confirmed";
export type SessionStatus = "draft" | "submitted" | "in_review" | "approved";
export type AnalysisStatus = "pending" | "complete" | "failed";

export type BoundingBox = {
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  confidence?: number;
};

export type InspectionItem = {
  id: string;
  code: string;
  sessionId: string;
  sortOrder: number;
  imageUrl: string;
  imageWidth?: number;
  imageHeight?: number;
  aiFindings?: string | null;
  aiRecommendation?: string | null;
  aiBoundingBoxes: BoundingBox[];
  aiConfidence?: number | null;
  aiAnalyzedAt?: string | null;
  findings?: string | null;
  recommendation?: string | null;
  rustGrade?: RustGrade | string | null;
  cof?: number | null;
  findingsPriority?: Priority | string | null;
  sapPriority?: Priority | string | null;
  equipmentType?: EquipmentType | string | null;
  equipmentId?: string | null;
  recommendationCode?: RecommendationCode | string | null;
  furtherInspection: boolean;
  openInsulation: boolean;
  scaffold: boolean;
  reviewStatus: ReviewStatus | string;
  analysisStatus: AnalysisStatus | string;
  analysisError?: string | null;
  editedFields: string[];
  createdAt: string;
  updatedAt: string;
};

export type InspectionSession = {
  id: string;
  status: SessionStatus | string;
  createdBy: string;
  systemReportNumber?: string | null;
  userReportNumber?: string | null;
  plant?: string | null;
  systemCode?: string | null;
  preparerName?: string | null;
  reviewerName?: string | null;
  approverName?: string | null;
  executiveSummary?: string | null;
  pdfUrl?: string | null;
  createdAt: string;
  updatedAt: string;
  submittedAt?: string | null;
  items: InspectionItem[];
};

export type InspectionItemPatch = Partial<{
  findings: string;
  recommendation: string;
  rustGrade: RustGrade;
  cof: number;
  findingsPriority: Priority;
  sapPriority: Priority;
  equipmentType: EquipmentType;
  equipmentId: string;
  recommendationCode: RecommendationCode;
  furtherInspection: boolean;
  openInsulation: boolean;
  scaffold: boolean;
  reviewStatus: ReviewStatus;
}>;

export type SubmitSessionPayload = Partial<{
  userReportNumber: string;
  plant: string;
  systemCode: string;
  preparerName: string;
  reviewerName: string;
  approverName: string;
}>;

export type ReportSummary = {
  id: string;
  systemReportNumber: string;
  userReportNumber?: string | null;
  plant?: string | null;
  systemCode?: string | null;
  preparerName?: string | null;
  reviewerName?: string | null;
  approverName?: string | null;
  equipmentType?: string | null;
  equipmentId?: string | null;
  status: SessionStatus | string;
  submittedAt?: string | null;
  totalFindings: number;
  highPriorityCount: number;
  tbsCount: number;
  avgCof?: number | null;
};

export type ReportListResponse = {
  reports: ReportSummary[];
  total: number;
  page: number;
  limit: number;
};

export type ReportDetail = ReportSummary & {
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  executiveSummary?: string | null;
  pdfUrl?: string | null;
  reviewedAt?: string | null;
  approvedAt?: string | null;
  reviewComment?: string | null;
  items: InspectionItem[];
};

export type ReportActionResponse = {
  id: string;
  status: string;
  message: string;
};
