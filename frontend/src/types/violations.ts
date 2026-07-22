export type ViolationType =
  | "no_helmet"
  | "triple_riding"
  | "red_light"
  | "wrong_way"
  | "lane_violation"
  | "illegal_parking"
  | "speeding"
  | "mobile_phone"
  | "seatbelt";

export type ReviewStatus =
  | "pending"
  | "confirmed"
  | "rejected";

export type ViolationEvent = {
  id: string;

  video_id: string;
  camera_id: string | null;
  processing_job_id: string | null;

  event_key: string;
  violation_type: ViolationType;
  review_status: ReviewStatus;

  occurred_at: string;
  frame_number: number | null;
  track_id: string | null;

  license_plate: string | null;

  detection_confidence: number | null;
  rule_confidence: number | null;
  ocr_confidence: number | null;

  evidence_image_key: string | null;
  evidence_clip_key: string | null;

  geometry: Record<string, unknown>;
  event_metadata: Record<string, unknown>;

  created_at: string;
  updated_at: string;
};

export type ViolationListResponse = {
  items: ViolationEvent[];
  total: number;
  offset: number;
  limit: number;
};

export type ViolationQuery = {
  offset?: number;
  limit?: number;
  violationType?: ViolationType;
  reviewStatus?: ReviewStatus;
  videoId?: string;
  processingJobId?: string;
  cameraId?: string;
};

export type ViolationReviewDecision =
  | "confirmed"
  | "rejected";

export type ViolationReviewPayload = {
  review_status: ViolationReviewDecision;
  reviewer: string | null;
  note: string | null;
};

export type ViolationReviewMetadata = {
  status: ReviewStatus;
  reviewed_at: string;
  reviewer: string | null;
  note: string | null;
};
