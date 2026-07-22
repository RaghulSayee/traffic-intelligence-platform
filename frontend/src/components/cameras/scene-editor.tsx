"use client";

import {
  AlertCircle,
  CheckCircle2,
  CircleDot,
  ImageIcon,
  Layers3,
  Route,
  Save,
  ShieldAlert,
  Signpost,
  Trash2,
  Undo2,
  X,
  Zap,
} from "lucide-react";
import Link from "next/link";
import {
  useMemo,
  useState,
} from "react";
import type {
  ChangeEvent,
  MouseEvent,
} from "react";

import {
  SceneReadinessPanel,
} from "@/components/cameras/scene-readiness-panel";
import {
  updateCameraScene,
} from "@/lib/api/cameras";
import type {
  Camera,
} from "@/types/cameras";
import type {
  CameraSceneConfiguration,
  LaneConfiguration,
  NormalizedPoint,
  SceneViolationType,
  SpeedCalibrationSegment,
  StopLineConfiguration,
  TrafficLightRegionConfiguration,
} from "@/types/camera-scene";

type DrawingTool =
  | "select"
  | "monitoring_zone"
  | "lane"
  | "traffic_light"
  | "stop_line"
  | "speed_segment";

type SceneEditorProps = {
  camera: Camera;
  initialScene: CameraSceneConfiguration;
};

const tools: Array<{
  value: DrawingTool;
  label: string;
  description: string;
}> = [
  {
    value: "select",
    label: "Select",
    description: "Inspect the scene.",
  },
  {
    value: "monitoring_zone",
    label: "Monitoring Zone",
    description: "Draw the complete monitored road area.",
  },
  {
    value: "lane",
    label: "Lane",
    description: "Draw a traffic-lane polygon.",
  },
  {
    value: "traffic_light",
    label: "Traffic Light",
    description: "Draw a signal-light region.",
  },
  {
    value: "stop_line",
    label: "Stop Line",
    description: "Click the two ends of a stop line.",
  },
  {
    value: "speed_segment",
    label: "Speed Segment",
    description: "Draw a known-distance calibration line.",
  },
];

const violationOptions: Array<{
  value: SceneViolationType;
  label: string;
}> = [
  {
    value: "no_helmet",
    label: "No Helmet",
  },
  {
    value: "triple_riding",
    label: "Triple Riding",
  },
  {
    value: "red_light",
    label: "Red Light",
  },
  {
    value: "wrong_way",
    label: "Wrong Way",
  },
  {
    value: "lane_violation",
    label: "Lane Violation",
  },
  {
    value: "speeding",
    label: "Speeding",
  },
];

function clamp(
  value: number,
): number {
  return Math.min(
    Math.max(value, 0),
    1,
  );
}

function toSvgPoint(
  point: NormalizedPoint,
): string {
  return `${point.x * 1000},${point.y * 1000}`;
}

function toSvgPoints(
  points: NormalizedPoint[],
): string {
  return points
    .map(toSvgPoint)
    .join(" ");
}

function getCentroid(
  points: NormalizedPoint[],
): NormalizedPoint {
  if (!points.length) {
    return {
      x: 0.5,
      y: 0.5,
    };
  }

  const total = points.reduce(
    (current, point) => ({
      x: current.x + point.x,
      y: current.y + point.y,
    }),
    {
      x: 0,
      y: 0,
    },
  );

  return {
    x: total.x / points.length,
    y: total.y / points.length,
  };
}

function sanitizeIdentifier(
  value: string,
): string {
  return value.replace(
    /[^A-Za-z0-9_-]/g,
    "",
  );
}

function nextIdentifier(
  prefix: string,
  existingIds: string[],
): string {
  let number = 1;

  while (
    existingIds.includes(
      `${prefix}-${number}`,
    )
  ) {
    number += 1;
  }

  return `${prefix}-${number}`;
}

function parseNullableNumber(
  value: string,
): number | null {
  if (!value.trim()) {
    return null;
  }

  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : null;
}

function findDuplicate(
  values: string[],
): string | null {
  const existing =
    new Set<string>();

  for (const value of values) {
    if (existing.has(value)) {
      return value;
    }

    existing.add(value);
  }

  return null;
}

export function SceneEditor({
  camera,
  initialScene,
}: SceneEditorProps) {
  const [
    scene,
    setScene,
  ] = useState(initialScene);

  const [
    selectedTool,
    setSelectedTool,
  ] = useState<DrawingTool>(
    "select",
  );

  const [
    draftPoints,
    setDraftPoints,
  ] = useState<
    NormalizedPoint[]
  >([]);

  const [
    referenceImage,
    setReferenceImage,
  ] = useState<string | null>(
    null,
  );

  const [
    aspectRatio,
    setAspectRatio,
  ] = useState(16 / 9);

  const [
    saving,
    setSaving,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const [
    successMessage,
    setSuccessMessage,
  ] = useState<string | null>(
    null,
  );

  const selectedToolInformation =
    tools.find(
      (tool) =>
        tool.value === selectedTool,
    );

  const isPolygonTool =
    selectedTool ===
      "monitoring_zone" ||
    selectedTool === "lane" ||
    selectedTool ===
      "traffic_light";

  const laneIds = useMemo(
    () =>
      scene.lanes.map(
        (lane) => lane.lane_id,
      ),
    [scene.lanes],
  );

  const signalIds = useMemo(
    () =>
      scene.traffic_light_regions.map(
        (region) =>
          region.region_id,
      ),
    [scene.traffic_light_regions],
  );

  function selectTool(
    tool: DrawingTool,
  ) {
    setSelectedTool(tool);
    setDraftPoints([]);
    setError(null);
    setSuccessMessage(null);
  }

  function handleReferenceImage(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    const reader =
      new FileReader();

    reader.onload = () => {
      if (
        typeof reader.result ===
        "string"
      ) {
        setReferenceImage(
          reader.result,
        );
      }
    };

    reader.readAsDataURL(file);
  }

  function handleCanvasClick(
    event: MouseEvent<SVGSVGElement>,
  ) {
    if (selectedTool === "select") {
      return;
    }

    const bounds =
      event.currentTarget.getBoundingClientRect();

    const point: NormalizedPoint = {
      x: clamp(
        (event.clientX -
          bounds.left) /
          bounds.width,
      ),
      y: clamp(
        (event.clientY -
          bounds.top) /
          bounds.height,
      ),
    };

    const nextPoints = [
      ...draftPoints,
      point,
    ];

    if (
      selectedTool ===
        "stop_line" ||
      selectedTool ===
        "speed_segment"
    ) {
      if (nextPoints.length === 2) {
        commitShape(nextPoints);
        return;
      }
    }

    setDraftPoints(nextPoints);
  }

  function commitShape(
    points: NormalizedPoint[],
  ) {
    setScene((current) => {
      if (
        selectedTool ===
        "monitoring_zone"
      ) {
        return {
          ...current,
          monitoring_zone: {
            points,
          },
        };
      }

      if (
        selectedTool === "lane"
      ) {
        const laneId =
          nextIdentifier(
            "lane",
            current.lanes.map(
              (lane) =>
                lane.lane_id,
            ),
          );

        const lane:
          LaneConfiguration = {
          lane_id: laneId,
          name: `Lane ${current.lanes.length + 1}`,
          polygon: {
            points,
          },
          allowed_direction: {
            x: 0,
            y: -1,
          },
          speed_limit_kph: null,
        };

        return {
          ...current,
          lanes: [
            ...current.lanes,
            lane,
          ],
        };
      }

      if (
        selectedTool ===
        "traffic_light"
      ) {
        const regionId =
          nextIdentifier(
            "signal",
            current
              .traffic_light_regions
              .map(
                (region) =>
                  region.region_id,
              ),
          );

        const region:
          TrafficLightRegionConfiguration =
          {
            region_id: regionId,
            name: `Traffic Signal ${current.traffic_light_regions.length + 1}`,
            polygon: {
              points,
            },
          };

        return {
          ...current,
          traffic_light_regions: [
            ...current
              .traffic_light_regions,
            region,
          ],
        };
      }

      if (
        selectedTool ===
        "stop_line"
      ) {
        const stopLineId =
          nextIdentifier(
            "stop",
            current.stop_lines.map(
              (line) =>
                line.stop_line_id,
            ),
          );

        const stopLine:
          StopLineConfiguration = {
          stop_line_id:
            stopLineId,
          lane_id: null,
          traffic_light_region_id:
            null,
          line: {
            start: points[0],
            end: points[1],
          },
        };

        return {
          ...current,
          stop_lines: [
            ...current.stop_lines,
            stopLine,
          ],
        };
      }

      if (
        selectedTool ===
        "speed_segment"
      ) {
        const segmentId =
          nextIdentifier(
            "distance",
            current
              .speed_calibration_segments
              .map(
                (segment) =>
                  segment.segment_id,
              ),
          );

        const segment:
          SpeedCalibrationSegment = {
          segment_id: segmentId,
          line: {
            start: points[0],
            end: points[1],
          },
          distance_meters: 5,
        };

        return {
          ...current,
          speed_calibration_segments:
            [
              ...current
                .speed_calibration_segments,
              segment,
            ],
        };
      }

      return current;
    });

    setDraftPoints([]);
    setError(null);
    setSuccessMessage(null);
  }

  function finishPolygon() {
    if (
      !isPolygonTool ||
      draftPoints.length < 3
    ) {
      setError(
        "A polygon requires at least three points.",
      );
      return;
    }

    commitShape(draftPoints);
  }

  function updateLane(
    index: number,
    changes:
      Partial<LaneConfiguration>,
  ) {
    setScene((current) => ({
      ...current,
      lanes: current.lanes.map(
        (lane, laneIndex) =>
          laneIndex === index
            ? {
                ...lane,
                ...changes,
              }
            : lane,
      ),
    }));
  }

  function updateSignal(
    index: number,
    changes: Partial<
      TrafficLightRegionConfiguration
    >,
  ) {
    setScene((current) => ({
      ...current,
      traffic_light_regions:
        current
          .traffic_light_regions
          .map(
            (
              region,
              regionIndex,
            ) =>
              regionIndex === index
                ? {
                    ...region,
                    ...changes,
                  }
                : region,
          ),
    }));
  }

  function updateStopLine(
    index: number,
    changes:
      Partial<StopLineConfiguration>,
  ) {
    setScene((current) => ({
      ...current,
      stop_lines:
        current.stop_lines.map(
          (line, lineIndex) =>
            lineIndex === index
              ? {
                  ...line,
                  ...changes,
                }
              : line,
        ),
    }));
  }

  function updateSpeedSegment(
    index: number,
    changes: Partial<
      SpeedCalibrationSegment
    >,
  ) {
    setScene((current) => ({
      ...current,
      speed_calibration_segments:
        current
          .speed_calibration_segments
          .map(
            (
              segment,
              segmentIndex,
            ) =>
              segmentIndex ===
              index
                ? {
                    ...segment,
                    ...changes,
                  }
                : segment,
          ),
    }));
  }

  function toggleViolation(
    violation: SceneViolationType,
  ) {
    setScene((current) => {
      const enabled =
        current.enabled_violations.includes(
          violation,
        );

      return {
        ...current,
        enabled_violations: enabled
          ? current.enabled_violations.filter(
              (item) =>
                item !== violation,
            )
          : [
              ...current.enabled_violations,
              violation,
            ],
      };
    });

    setSuccessMessage(null);
  }

  function validateScene():
    | string
    | null {
    const duplicateLane =
      findDuplicate(
        scene.lanes.map(
          (lane) => lane.lane_id,
        ),
      );

    if (duplicateLane) {
      return `Duplicate lane ID: ${duplicateLane}`;
    }

    const duplicateSignal =
      findDuplicate(
        scene.traffic_light_regions.map(
          (region) =>
            region.region_id,
        ),
      );

    if (duplicateSignal) {
      return `Duplicate signal ID: ${duplicateSignal}`;
    }

    const duplicateStopLine =
      findDuplicate(
        scene.stop_lines.map(
          (line) =>
            line.stop_line_id,
        ),
      );

    if (duplicateStopLine) {
      return `Duplicate stop-line ID: ${duplicateStopLine}`;
    }

    for (const lane of scene.lanes) {
      if (!lane.lane_id) {
        return "Every lane requires an ID.";
      }

      if (
        lane.allowed_direction.x ===
          0 &&
        lane.allowed_direction.y ===
          0
      ) {
        return `Lane ${lane.lane_id} cannot have a zero direction vector.`;
      }
    }

    const validLaneIds =
      new Set(laneIds);

    const validSignalIds =
      new Set(signalIds);

    for (
      const stopLine
      of scene.stop_lines
    ) {
      if (
        stopLine.lane_id &&
        !validLaneIds.has(
          stopLine.lane_id,
        )
      ) {
        return `Stop line ${stopLine.stop_line_id} references an unknown lane.`;
      }

      if (
        stopLine
          .traffic_light_region_id &&
        !validSignalIds.has(
          stopLine
            .traffic_light_region_id,
        )
      ) {
        return `Stop line ${stopLine.stop_line_id} references an unknown traffic signal.`;
      }
    }

    return null;
  }

  async function saveScene() {
    const validationError =
      validateScene();

    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const updatedScene =
        await updateCameraScene(
          camera.id,
          scene,
        );

      setScene(updatedScene);

      setSuccessMessage(
        "Camera scene saved successfully.",
      );
    } catch (
      requestError
    ) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The camera scene could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <Layers3
            size={20}
            className="text-cyan-700"
          />

          <p className="mt-3 text-xs text-slate-500">
            Monitoring zone
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {scene.monitoring_zone
              ? "Configured"
              : "Missing"}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <Route
            size={20}
            className="text-cyan-700"
          />

          <p className="mt-3 text-xs text-slate-500">
            Lanes
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {scene.lanes.length}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <CircleDot
            size={20}
            className="text-cyan-700"
          />

          <p className="mt-3 text-xs text-slate-500">
            Signals
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {
              scene
                .traffic_light_regions
                .length
            }
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <Signpost
            size={20}
            className="text-cyan-700"
          />

          <p className="mt-3 text-xs text-slate-500">
            Stop lines
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {scene.stop_lines.length}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <Zap
            size={20}
            className="text-cyan-700"
          />

          <p className="mt-3 text-xs text-slate-500">
            Speed segments
          </p>

          <p className="mt-1 text-xl font-bold text-slate-950">
            {
              scene
                .speed_calibration_segments
                .length
            }
          </p>
        </article>
      </section>

      <SceneReadinessPanel
        scene={scene}
      />

      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.75fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
            <div>
              <h2 className="font-semibold text-slate-950">
                Scene canvas
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Select a tool and click on the
                image to create normalized
                scene geometry.
              </p>
            </div>

            <label className="inline-flex h-10 cursor-pointer items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-600 hover:bg-slate-50">
              <ImageIcon size={17} />
              Reference image

              <input
                type="file"
                accept="image/*"
                onChange={
                  handleReferenceImage
                }
                className="hidden"
              />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            {tools.map((tool) => (
              <button
                key={tool.value}
                type="button"
                onClick={() =>
                  selectTool(
                    tool.value,
                  )
                }
                className={[
                  "rounded-xl border px-3 py-2 text-sm font-semibold",
                  selectedTool ===
                  tool.value
                    ? "border-cyan-400 bg-cyan-50 text-cyan-800 ring-4 ring-cyan-100"
                    : "border-slate-200 text-slate-600 hover:bg-slate-50",
                ].join(" ")}
              >
                {tool.label}
              </button>
            ))}
          </div>

          <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
            <span className="font-semibold text-slate-900">
              {
                selectedToolInformation
                  ?.label
              }
              :
            </span>{" "}
            {
              selectedToolInformation
                ?.description
            }
          </div>

          <div
            className="relative mt-5 overflow-hidden rounded-2xl border border-slate-300 bg-slate-950"
            style={{
              aspectRatio,
            }}
          >
            {referenceImage ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={referenceImage}
                alt="Camera scene reference"
                onLoad={(event) => {
                  const image =
                    event.currentTarget;

                  if (
                    image.naturalWidth >
                      0 &&
                    image.naturalHeight >
                      0
                  ) {
                    setAspectRatio(
                      image.naturalWidth /
                        image.naturalHeight,
                    );
                  }
                }}
                className="absolute inset-0 h-full w-full object-fill"
              />
            ) : (
              <div
                className="absolute inset-0 flex flex-col items-center justify-center text-center text-slate-400"
                style={{
                  backgroundImage:
                    "linear-gradient(rgba(148,163,184,.12) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,.12) 1px, transparent 1px)",
                  backgroundSize:
                    "40px 40px",
                }}
              >
                <ImageIcon
                  size={40}
                />

                <p className="mt-3 text-sm font-semibold">
                  Add a camera screenshot
                </p>

                <p className="mt-1 text-xs">
                  Drawing is also available
                  without an image.
                </p>
              </div>
            )}

            <svg
              viewBox="0 0 1000 1000"
              preserveAspectRatio="none"
              onClick={
                handleCanvasClick
              }
              className={[
                "absolute inset-0 h-full w-full",
                selectedTool ===
                "select"
                  ? "cursor-default"
                  : "cursor-crosshair",
              ].join(" ")}
            >
              <defs>
                <marker
                  id="direction-arrow"
                  markerWidth="10"
                  markerHeight="10"
                  refX="8"
                  refY="3"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path
                    d="M0,0 L0,6 L9,3 z"
                    fill="#22d3ee"
                  />
                </marker>
              </defs>

              {scene.monitoring_zone ? (
                <polygon
                  points={toSvgPoints(
                    scene
                      .monitoring_zone
                      .points,
                  )}
                  fill="rgba(14,165,233,.12)"
                  stroke="#38bdf8"
                  strokeWidth="5"
                  strokeDasharray="18 10"
                  vectorEffect="non-scaling-stroke"
                  pointerEvents="none"
                />
              ) : null}

              {scene.lanes.map(
                (lane) => {
                  const center =
                    getCentroid(
                      lane.polygon.points,
                    );

                  return (
                    <g
                      key={
                        lane.lane_id
                      }
                      pointerEvents="none"
                    >
                      <polygon
                        points={toSvgPoints(
                          lane.polygon
                            .points,
                        )}
                        fill="rgba(34,197,94,.16)"
                        stroke="#22c55e"
                        strokeWidth="5"
                        vectorEffect="non-scaling-stroke"
                      />

                      <line
                        x1={
                          center.x *
                          1000
                        }
                        y1={
                          center.y *
                          1000
                        }
                        x2={
                          (
                            center.x +
                            lane
                              .allowed_direction
                              .x *
                              0.12
                          ) * 1000
                        }
                        y2={
                          (
                            center.y +
                            lane
                              .allowed_direction
                              .y *
                              0.12
                          ) * 1000
                        }
                        stroke="#22d3ee"
                        strokeWidth="7"
                        markerEnd="url(#direction-arrow)"
                        vectorEffect="non-scaling-stroke"
                      />
                    </g>
                  );
                },
              )}

              {scene.traffic_light_regions.map(
                (region) => (
                  <polygon
                    key={
                      region.region_id
                    }
                    points={toSvgPoints(
                      region.polygon
                        .points,
                    )}
                    fill="rgba(239,68,68,.25)"
                    stroke="#ef4444"
                    strokeWidth="5"
                    vectorEffect="non-scaling-stroke"
                    pointerEvents="none"
                  />
                ),
              )}

              {scene.stop_lines.map(
                (stopLine) => (
                  <line
                    key={
                      stopLine.stop_line_id
                    }
                    x1={
                      stopLine.line
                        .start.x * 1000
                    }
                    y1={
                      stopLine.line
                        .start.y * 1000
                    }
                    x2={
                      stopLine.line
                        .end.x * 1000
                    }
                    y2={
                      stopLine.line
                        .end.y * 1000
                    }
                    stroke="#facc15"
                    strokeWidth="9"
                    vectorEffect="non-scaling-stroke"
                    pointerEvents="none"
                  />
                ),
              )}

              {scene.speed_calibration_segments.map(
                (segment) => (
                  <line
                    key={
                      segment.segment_id
                    }
                    x1={
                      segment.line
                        .start.x * 1000
                    }
                    y1={
                      segment.line
                        .start.y * 1000
                    }
                    x2={
                      segment.line
                        .end.x * 1000
                    }
                    y2={
                      segment.line
                        .end.y * 1000
                    }
                    stroke="#a855f7"
                    strokeWidth="7"
                    strokeDasharray="16 10"
                    vectorEffect="non-scaling-stroke"
                    pointerEvents="none"
                  />
                ),
              )}

              {draftPoints.length ? (
                <g pointerEvents="none">
                  <polyline
                    points={toSvgPoints(
                      draftPoints,
                    )}
                    fill={
                      isPolygonTool
                        ? "rgba(6,182,212,.15)"
                        : "none"
                    }
                    stroke="#06b6d4"
                    strokeWidth="6"
                    strokeDasharray="14 8"
                    vectorEffect="non-scaling-stroke"
                  />

                  {draftPoints.map(
                    (point, index) => (
                      <circle
                        key={`${point.x}-${point.y}-${index}`}
                        cx={
                          point.x *
                          1000
                        }
                        cy={
                          point.y *
                          1000
                        }
                        r="10"
                        fill="#ffffff"
                        stroke="#06b6d4"
                        strokeWidth="5"
                        vectorEffect="non-scaling-stroke"
                      />
                    ),
                  )}
                </g>
              ) : null}
            </svg>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-500">
              Draft points:{" "}
              <span className="font-semibold text-slate-800">
                {draftPoints.length}
              </span>
            </p>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={
                  !draftPoints.length
                }
                onClick={() =>
                  setDraftPoints(
                    (current) =>
                      current.slice(
                        0,
                        -1,
                      ),
                  )
                }
                className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40"
              >
                <Undo2 size={16} />
                Undo point
              </button>

              <button
                type="button"
                disabled={
                  !draftPoints.length
                }
                onClick={() =>
                  setDraftPoints([])
                }
                className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40"
              >
                <X size={16} />
                Cancel
              </button>

              {isPolygonTool ? (
                <button
                  type="button"
                  disabled={
                    draftPoints.length <
                    3
                  }
                  onClick={
                    finishPolygon
                  }
                  className="inline-flex h-9 items-center gap-2 rounded-lg bg-cyan-500 px-4 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-40"
                >
                  <CheckCircle2
                    size={16}
                  />
                  Complete shape
                </button>
              ) : null}
            </div>
          </div>
        </article>

        <aside className="space-y-6">
          <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="font-semibold text-slate-950">
              Enabled violations
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Select the rules that should
              run for this camera.
            </p>

            <div className="mt-4 space-y-2">
              {violationOptions.map(
                (violation) => (
                  <label
                    key={
                      violation.value
                    }
                    className="flex cursor-pointer items-center justify-between rounded-xl border border-slate-200 px-3 py-3 hover:bg-slate-50"
                  >
                    <span className="text-sm font-medium text-slate-700">
                      {violation.label}
                    </span>

                    <input
                      type="checkbox"
                      checked={scene.enabled_violations.includes(
                        violation.value,
                      )}
                      onChange={() =>
                        toggleViolation(
                          violation.value,
                        )
                      }
                      className="h-4 w-4 accent-cyan-500"
                    />
                  </label>
                ),
              )}
            </div>
          </article>

          {scene.monitoring_zone ? (
            <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="font-semibold text-slate-950">
                    Monitoring zone
                  </h2>

                  <p className="mt-1 text-xs text-slate-400">
                    {
                      scene
                        .monitoring_zone
                        .points.length
                    }{" "}
                    points
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    setScene(
                      (current) => ({
                        ...current,
                        monitoring_zone:
                          null,
                      }),
                    )
                  }
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-rose-200 text-rose-600 hover:bg-rose-50"
                  aria-label="Delete monitoring zone"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </article>
          ) : null}

          <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="font-semibold text-slate-950">
              Scene legend
            </h2>

            <div className="mt-4 space-y-3 text-sm text-slate-600">
              <p>
                Blue dashed: monitoring zone
              </p>
              <p>
                Green: configured lanes
              </p>
              <p>
                Cyan arrow: allowed direction
              </p>
              <p>
                Red: traffic-light region
              </p>
              <p>
                Yellow: stop line
              </p>
              <p>
                Purple dashed: speed calibration
              </p>
            </div>
          </article>
        </aside>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            Lanes
          </h2>

          <div className="mt-4 space-y-4">
            {scene.lanes.map(
              (lane, index) => (
                <div
                  key={`${lane.lane_id}-${index}`}
                  className="rounded-xl border border-slate-200 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-slate-900">
                      Lane {index + 1}
                    </p>

                    <button
                      type="button"
                      onClick={() =>
                        setScene(
                          (current) => ({
                            ...current,
                            lanes:
                              current.lanes.filter(
                                (
                                  _,
                                  laneIndex,
                                ) =>
                                  laneIndex !==
                                  index,
                              ),
                          }),
                        )
                      }
                      className="text-rose-600"
                      aria-label={`Delete lane ${lane.lane_id}`}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <label>
                      <span className="text-xs font-semibold text-slate-500">
                        Lane ID
                      </span>

                      <input
                        value={
                          lane.lane_id
                        }
                        onChange={(
                          event,
                        ) =>
                          updateLane(
                            index,
                            {
                              lane_id:
                                sanitizeIdentifier(
                                  event
                                    .target
                                    .value,
                                ),
                            },
                          )
                        }
                        className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
                      />
                    </label>

                    <label>
                      <span className="text-xs font-semibold text-slate-500">
                        Name
                      </span>

                      <input
                        value={
                          lane.name ?? ""
                        }
                        onChange={(
                          event,
                        ) =>
                          updateLane(
                            index,
                            {
                              name:
                                event
                                  .target
                                  .value ||
                                null,
                            },
                          )
                        }
                        className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
                      />
                    </label>

                    <label>
                      <span className="text-xs font-semibold text-slate-500">
                        Direction X
                      </span>

                      <input
                        type="number"
                        step="0.1"
                        value={
                          lane
                            .allowed_direction
                            .x
                        }
                        onChange={(
                          event,
                        ) =>
                          updateLane(
                            index,
                            {
                              allowed_direction:
                                {
                                  ...lane.allowed_direction,
                                  x:
                                    Number(
                                      event
                                        .target
                                        .value,
                                    ) ||
                                    0,
                                },
                            },
                          )
                        }
                        className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
                      />
                    </label>

                    <label>
                      <span className="text-xs font-semibold text-slate-500">
                        Direction Y
                      </span>

                      <input
                        type="number"
                        step="0.1"
                        value={
                          lane
                            .allowed_direction
                            .y
                        }
                        onChange={(
                          event,
                        ) =>
                          updateLane(
                            index,
                            {
                              allowed_direction:
                                {
                                  ...lane.allowed_direction,
                                  y:
                                    Number(
                                      event
                                        .target
                                        .value,
                                    ) ||
                                    0,
                                },
                            },
                          )
                        }
                        className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
                      />
                    </label>

                    <label className="sm:col-span-2">
                      <span className="text-xs font-semibold text-slate-500">
                        Speed limit KPH
                      </span>

                      <input
                        type="number"
                        min="1"
                        max="300"
                        value={
                          lane.speed_limit_kph ??
                          ""
                        }
                        onChange={(
                          event,
                        ) =>
                          updateLane(
                            index,
                            {
                              speed_limit_kph:
                                parseNullableNumber(
                                  event
                                    .target
                                    .value,
                                ),
                            },
                          )
                        }
                        className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
                      />
                    </label>
                  </div>
                </div>
              ),
            )}

            {!scene.lanes.length ? (
              <p className="rounded-xl border border-dashed border-slate-200 p-5 text-center text-sm text-slate-400">
                No lanes configured.
              </p>
            ) : null}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            Traffic-light regions
          </h2>

          <div className="mt-4 space-y-4">
            {scene.traffic_light_regions.map(
              (region, index) => (
                <div
                  key={`${region.region_id}-${index}`}
                  className="rounded-xl border border-slate-200 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-slate-900">
                      Signal {index + 1}
                    </p>

                    <button
                      type="button"
                      onClick={() =>
                        setScene(
                          (current) => ({
                            ...current,
                            traffic_light_regions:
                              current.traffic_light_regions.filter(
                                (
                                  _,
                                  regionIndex,
                                ) =>
                                  regionIndex !==
                                  index,
                              ),
                          }),
                        )
                      }
                      className="text-rose-600"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <label>
                      <span className="text-xs font-semibold text-slate-500">
                        Region ID
                      </span>

                      <input
                        value={
                          region.region_id
                        }
                        onChange={(
                          event,
                        ) =>
                          updateSignal(
                            index,
                            {
                              region_id:
                                sanitizeIdentifier(
                                  event
                                    .target
                                    .value,
                                ),
                            },
                          )
                        }
                        className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
                      />
                    </label>

                    <label>
                      <span className="text-xs font-semibold text-slate-500">
                        Name
                      </span>

                      <input
                        value={
                          region.name ?? ""
                        }
                        onChange={(
                          event,
                        ) =>
                          updateSignal(
                            index,
                            {
                              name:
                                event
                                  .target
                                  .value ||
                                null,
                            },
                          )
                        }
                        className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
                      />
                    </label>
                  </div>
                </div>
              ),
            )}

            {!scene
              .traffic_light_regions
              .length ? (
              <p className="rounded-xl border border-dashed border-slate-200 p-5 text-center text-sm text-slate-400">
                No traffic-light regions configured.
              </p>
            ) : null}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            Stop-line relationships
          </h2>

          <div className="mt-4 space-y-4">
            {scene.stop_lines.map(
              (stopLine, index) => (
                <div
                  key={`${stopLine.stop_line_id}-${index}`}
                  className="rounded-xl border border-slate-200 p-4"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-900">
                      Stop line {index + 1}
                    </p>

                    <button
                      type="button"
                      onClick={() =>
                        setScene(
                          (current) => ({
                            ...current,
                            stop_lines:
                              current.stop_lines.filter(
                                (
                                  _,
                                  lineIndex,
                                ) =>
                                  lineIndex !==
                                  index,
                              ),
                          }),
                        )
                      }
                      className="text-rose-600"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  <div className="mt-3 grid gap-3">
                    <input
                      value={
                        stopLine.stop_line_id
                      }
                      onChange={(event) =>
                        updateStopLine(
                          index,
                          {
                            stop_line_id:
                              sanitizeIdentifier(
                                event.target
                                  .value,
                              ),
                          },
                        )
                      }
                      className="h-10 rounded-lg border border-slate-200 px-3 text-sm"
                      placeholder="Stop-line ID"
                    />

                    <select
                      value={
                        stopLine.lane_id ??
                        ""
                      }
                      onChange={(event) =>
                        updateStopLine(
                          index,
                          {
                            lane_id:
                              event.target
                                .value ||
                              null,
                          },
                        )
                      }
                      className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm"
                    >
                      <option value="">
                        No lane connected
                      </option>

                      {scene.lanes.map(
                        (lane) => (
                          <option
                            key={
                              lane.lane_id
                            }
                            value={
                              lane.lane_id
                            }
                          >
                            {lane.name ??
                              lane.lane_id}
                          </option>
                        ),
                      )}
                    </select>

                    <select
                      value={
                        stopLine
                          .traffic_light_region_id ??
                        ""
                      }
                      onChange={(event) =>
                        updateStopLine(
                          index,
                          {
                            traffic_light_region_id:
                              event.target
                                .value ||
                              null,
                          },
                        )
                      }
                      className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm"
                    >
                      <option value="">
                        No signal connected
                      </option>

                      {scene.traffic_light_regions.map(
                        (region) => (
                          <option
                            key={
                              region.region_id
                            }
                            value={
                              region.region_id
                            }
                          >
                            {region.name ??
                              region.region_id}
                          </option>
                        ),
                      )}
                    </select>
                  </div>
                </div>
              ),
            )}

            {!scene.stop_lines.length ? (
              <p className="rounded-xl border border-dashed border-slate-200 p-5 text-center text-sm text-slate-400">
                No stop lines configured.
              </p>
            ) : null}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-950">
            Speed calibration
          </h2>

          <div className="mt-4 space-y-4">
            {scene.speed_calibration_segments.map(
              (segment, index) => (
                <div
                  key={`${segment.segment_id}-${index}`}
                  className="rounded-xl border border-slate-200 p-4"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-900">
                      Segment {index + 1}
                    </p>

                    <button
                      type="button"
                      onClick={() =>
                        setScene(
                          (current) => ({
                            ...current,
                            speed_calibration_segments:
                              current.speed_calibration_segments.filter(
                                (
                                  _,
                                  segmentIndex,
                                ) =>
                                  segmentIndex !==
                                  index,
                              ),
                          }),
                        )
                      }
                      className="text-rose-600"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <input
                      value={
                        segment.segment_id
                      }
                      onChange={(event) =>
                        updateSpeedSegment(
                          index,
                          {
                            segment_id:
                              sanitizeIdentifier(
                                event.target
                                  .value,
                              ),
                          },
                        )
                      }
                      className="h-10 rounded-lg border border-slate-200 px-3 text-sm"
                      placeholder="Segment ID"
                    />

                    <input
                      type="number"
                      min="0.1"
                      max="5000"
                      step="0.1"
                      value={
                        segment.distance_meters
                      }
                      onChange={(event) =>
                        updateSpeedSegment(
                          index,
                          {
                            distance_meters:
                              Number(
                                event.target
                                  .value,
                              ) || 0.1,
                          },
                        )
                      }
                      className="h-10 rounded-lg border border-slate-200 px-3 text-sm"
                      placeholder="Distance in meters"
                    />
                  </div>
                </div>
              ),
            )}

            {!scene
              .speed_calibration_segments
              .length ? (
              <p className="rounded-xl border border-dashed border-slate-200 p-5 text-center text-sm text-slate-400">
                No speed calibration segments configured.
              </p>
            ) : null}
          </div>
        </article>
      </section>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <AlertCircle
            size={18}
            className="mt-0.5 shrink-0"
          />

          {error}
        </div>
      ) : null}

      {successMessage ? (
        <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          <CheckCircle2
            size={18}
            className="mt-0.5 shrink-0"
          />

          {successMessage}
        </div>
      ) : null}

      <div className="sticky bottom-4 z-20 flex flex-wrap justify-end gap-3">
        <Link
          href={`/cameras/${camera.id}/test`}
          className="inline-flex h-12 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-6 text-sm font-semibold text-slate-700 shadow-lg hover:bg-slate-50"
        >
          <ShieldAlert size={19} />
          Test scene
        </Link>

        <button
          type="button"
          onClick={saveScene}
          disabled={saving}
          className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-6 text-sm font-semibold text-slate-950 shadow-lg hover:bg-cyan-400 disabled:opacity-60"
        >
          <Save size={19} />

          {saving
            ? "Saving scene..."
            : "Save scene"}
        </button>
      </div>
    </div>
  );
}
