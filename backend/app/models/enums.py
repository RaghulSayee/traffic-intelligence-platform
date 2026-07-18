from enum import StrEnum


class CameraStatus(StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class VideoSourceType(StrEnum):
    UPLOAD = "upload"
    CAMERA_RECORDING = "camera_recording"
    LIVE_STREAM = "live_stream"


class VideoStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ViolationType(StrEnum):
    NO_HELMET = "no_helmet"
    TRIPLE_RIDING = "triple_riding"
    RED_LIGHT = "red_light"
    WRONG_WAY = "wrong_way"
    LANE_VIOLATION = "lane_violation"
    ILLEGAL_PARKING = "illegal_parking"
    SPEEDING = "speeding"
    MOBILE_PHONE = "mobile_phone"
    SEATBELT = "seatbelt"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"