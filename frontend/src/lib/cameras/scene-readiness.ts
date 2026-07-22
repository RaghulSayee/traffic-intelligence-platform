import type {
  CameraSceneConfiguration,
  NormalizedDirection,
  NormalizedLine,
  NormalizedPolygon,
  SceneViolationType,
} from "@/types/camera-scene";

export type SceneRequirementStatus =
  | "pass"
  | "warning"
  | "fail";

export type SceneRequirement = {
  id: string;
  label: string;
  status: SceneRequirementStatus;
  detail: string;
};

export type SceneRuleReadiness = {
  violationType: SceneViolationType;
  label: string;
  enabled: boolean;
  ready: boolean;
  requirements: SceneRequirement[];
};

const violationLabels: Record<
  SceneViolationType,
  string
> = {
  no_helmet: "No Helmet",
  triple_riding: "Triple Riding",
  red_light: "Red Light",
  wrong_way: "Wrong Way",
  lane_violation: "Lane Violation",
  speeding: "Speeding",
};

function isValidPolygon(
  polygon: NormalizedPolygon | null,
): boolean {
  return Boolean(
    polygon &&
      Array.isArray(polygon.points) &&
      polygon.points.length >= 3,
  );
}

function isValidLine(
  line: NormalizedLine,
): boolean {
  const horizontalDifference =
    Math.abs(
      line.start.x - line.end.x,
    );

  const verticalDifference =
    Math.abs(
      line.start.y - line.end.y,
    );

  return (
    horizontalDifference > 0.0001 ||
    verticalDifference > 0.0001
  );
}

function isValidDirection(
  direction: NormalizedDirection,
): boolean {
  return (
    Math.abs(direction.x) > 0.0001 ||
    Math.abs(direction.y) > 0.0001
  );
}

function requirement({
  id,
  label,
  passed,
  successDetail,
  failureDetail,
  optional = false,
}: {
  id: string;
  label: string;
  passed: boolean;
  successDetail: string;
  failureDetail: string;
  optional?: boolean;
}): SceneRequirement {
  return {
    id,
    label,
    status: passed
      ? "pass"
      : optional
        ? "warning"
        : "fail",
    detail: passed
      ? successDetail
      : failureDetail,
  };
}

export function buildSceneReadiness(
  scene: CameraSceneConfiguration,
): SceneRuleReadiness[] {
  const validLanes =
    scene.lanes.filter((lane) =>
      isValidPolygon(
        lane.polygon,
      ),
    );

  const laneIds =
    new Set(
      validLanes.map(
        (lane) => lane.lane_id,
      ),
    );

  const validSignals =
    scene.traffic_light_regions.filter(
      (region) =>
        isValidPolygon(
          region.polygon,
        ),
    );

  const signalIds =
    new Set(
      validSignals.map(
        (region) =>
          region.region_id,
      ),
    );

  const validStopLines =
    scene.stop_lines.filter(
      (stopLine) =>
        isValidLine(
          stopLine.line,
        ),
    );

  const linkedStopLines =
    validStopLines.filter(
      (stopLine) =>
        Boolean(
          stopLine.lane_id &&
            laneIds.has(
              stopLine.lane_id,
            ) &&
            stopLine
              .traffic_light_region_id &&
            signalIds.has(
              stopLine
                .traffic_light_region_id,
            ),
        ),
    );

  const lanesWithDirection =
    validLanes.filter(
      (lane) =>
        isValidDirection(
          lane.allowed_direction,
        ),
    );

  const lanesWithSpeedLimit =
    validLanes.filter(
      (lane) =>
        typeof lane.speed_limit_kph ===
          "number" &&
        lane.speed_limit_kph > 0,
    );

  const validCalibrationSegments =
    scene.speed_calibration_segments.filter(
      (segment) =>
        segment.distance_meters > 0 &&
        isValidLine(segment.line),
    );

  const hasMonitoringZone =
    isValidPolygon(
      scene.monitoring_zone,
    );

  const requirementsByRule: Record<
    SceneViolationType,
    SceneRequirement[]
  > = {
    no_helmet: [
      requirement({
        id: "monitoring-zone",
        label: "Monitoring zone",
        passed: hasMonitoringZone,
        successDetail:
          "Detection is limited to the configured roadway.",
        failureDetail:
          "Optional: add a monitoring zone to exclude sidewalks and irrelevant areas.",
        optional: true,
      }),
    ],

    triple_riding: [
      requirement({
        id: "monitoring-zone",
        label: "Monitoring zone",
        passed: hasMonitoringZone,
        successDetail:
          "Detection is limited to the configured roadway.",
        failureDetail:
          "Optional: add a monitoring zone to reduce irrelevant detections.",
        optional: true,
      }),
    ],

    lane_violation: [
      requirement({
        id: "lane-polygon",
        label: "Lane polygon",
        passed:
          validLanes.length > 0,
        successDetail:
          `${validLanes.length} valid lane polygon configured.`,
        failureDetail:
          "Draw at least one lane polygon.",
      }),

      requirement({
        id: "monitoring-zone",
        label: "Monitoring zone",
        passed: hasMonitoringZone,
        successDetail:
          "A monitoring zone limits lane analysis to the roadway.",
        failureDetail:
          "Recommended: configure a monitoring zone.",
        optional: true,
      }),
    ],

    wrong_way: [
      requirement({
        id: "lane-polygon",
        label: "Lane polygon",
        passed:
          validLanes.length > 0,
        successDetail:
          `${validLanes.length} valid lane polygon configured.`,
        failureDetail:
          "Draw at least one lane polygon.",
      }),

      requirement({
        id: "lane-direction",
        label: "Allowed lane direction",
        passed:
          validLanes.length > 0 &&
          lanesWithDirection.length ===
            validLanes.length,
        successDetail:
          "Every configured lane has a non-zero direction vector.",
        failureDetail:
          "Set a non-zero X/Y direction for every lane.",
      }),

      requirement({
        id: "monitoring-zone",
        label: "Monitoring zone",
        passed: hasMonitoringZone,
        successDetail:
          "Wrong-way tracking is limited to the monitored roadway.",
        failureDetail:
          "Recommended: configure a monitoring zone.",
        optional: true,
      }),
    ],

    red_light: [
      requirement({
        id: "lane-polygon",
        label: "Lane polygon",
        passed:
          validLanes.length > 0,
        successDetail:
          `${validLanes.length} valid lane polygon configured.`,
        failureDetail:
          "Draw the lane controlled by the traffic signal.",
      }),

      requirement({
        id: "traffic-light-region",
        label: "Traffic-light region",
        passed:
          validSignals.length > 0,
        successDetail:
          `${validSignals.length} traffic-light region configured.`,
        failureDetail:
          "Draw a region tightly around the traffic signal.",
      }),

      requirement({
        id: "stop-line",
        label: "Stop line",
        passed:
          validStopLines.length > 0,
        successDetail:
          `${validStopLines.length} valid stop line configured.`,
        failureDetail:
          "Draw a stop line using two points.",
      }),

      requirement({
        id: "stop-line-relationship",
        label:
          "Lane and signal relationship",
        passed:
          linkedStopLines.length > 0,
        successDetail:
          `${linkedStopLines.length} stop line correctly connects a lane and traffic signal.`,
        failureDetail:
          "Connect a stop line to both a valid lane and traffic-light region.",
      }),
    ],

    speeding: [
      requirement({
        id: "lane-polygon",
        label: "Lane polygon",
        passed:
          validLanes.length > 0,
        successDetail:
          `${validLanes.length} valid lane polygon configured.`,
        failureDetail:
          "Draw at least one lane polygon.",
      }),

      requirement({
        id: "speed-limit",
        label: "Lane speed limit",
        passed:
          lanesWithSpeedLimit.length > 0,
        successDetail:
          `${lanesWithSpeedLimit.length} lane has a configured speed limit.`,
        failureDetail:
          "Enter a speed limit in KPH for at least one lane.",
      }),

      requirement({
        id: "speed-calibration",
        label: "Distance calibration",
        passed:
          validCalibrationSegments.length >
          0,
        successDetail:
          `${validCalibrationSegments.length} known-distance segment configured.`,
        failureDetail:
          "Draw a calibration segment and enter its real-world distance.",
      }),
    ],
  };

  return (
    Object.keys(
      violationLabels,
    ) as SceneViolationType[]
  ).map((violationType) => {
    const requirements =
      requirementsByRule[
        violationType
      ];

    const enabled =
      scene.enabled_violations.includes(
        violationType,
      );

    const ready =
      requirements.every(
        (item) =>
          item.status !== "fail",
      );

    return {
      violationType,
      label:
        violationLabels[
          violationType
        ],
      enabled,
      ready,
      requirements,
    };
  });
}

export function getEnabledSceneReadiness(
  scene: CameraSceneConfiguration,
): SceneRuleReadiness[] {
  return buildSceneReadiness(
    scene,
  ).filter(
    (rule) => rule.enabled,
  );
}
