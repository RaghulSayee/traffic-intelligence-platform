"use client";

import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Eye,
  Filter,
  RefreshCw,
  Search,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  PaginationControls,
} from "@/components/ui/pagination-controls";
import {
  getViolations,
} from "@/lib/api/violations";
import {
  MobileTableNotice,
} from "@/components/ui/mobile-table-notice";

import type {
  ReviewStatus,
  ViolationEvent,
  ViolationListResponse,
  ViolationType,
} from "@/types/violations";

type CameraLookup = {
  id: string;
  name: string;
  location: string | null;
};

type VideoLookup = {
  id: string;
  original_filename: string;
};

type ViolationsBrowserProps = {
  initialResponse: ViolationListResponse;
  cameras: CameraLookup[];
  videos: VideoLookup[];
};

const violationTypes: Array<{
  value: ViolationType;
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
    value: "illegal_parking",
    label: "Illegal Parking",
  },
  {
    value: "speeding",
    label: "Speeding",
  },
  {
    value: "mobile_phone",
    label: "Mobile Phone",
  },
  {
    value: "seatbelt",
    label: "Seatbelt",
  },
];

const reviewStatuses: Array<{
  value: ReviewStatus;
  label: string;
}> = [
  {
    value: "pending",
    label: "Pending",
  },
  {
    value: "confirmed",
    label: "Confirmed",
  },
  {
    value: "rejected",
    label: "Rejected",
  },
];

const statusStyles: Record<
  ReviewStatus,
  string
> = {
  pending:
    "bg-amber-50 text-amber-700",
  confirmed:
    "bg-emerald-50 text-emerald-700",
  rejected:
    "bg-rose-50 text-rose-700",
};

const statusIcons = {
  pending: Clock3,
  confirmed: CheckCircle2,
  rejected: XCircle,
};

function formatLabel(
  value: string,
): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(" ");
}

function formatDate(
  value: string,
): string {
  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(new Date(value));
}

function getConfidence(
  violation: ViolationEvent,
): number | null {
  const confidenceValues = [
    violation.detection_confidence,
    violation.rule_confidence,
    violation.ocr_confidence,
  ].filter(
    (value): value is number =>
      typeof value === "number",
  );

  if (!confidenceValues.length) {
    return null;
  }

  return Math.max(
    ...confidenceValues,
  );
}

function createUpdatedTimeLabel(): string {
  return new Intl.DateTimeFormat(
    "en-US",
    {
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    },
  ).format(new Date());
}

export function ViolationsBrowser({
  initialResponse,
  cameras,
  videos,
}: ViolationsBrowserProps) {
  const [
    response,
    setResponse,
  ] = useState(initialResponse);

  const [
    selectedType,
    setSelectedType,
  ] = useState<
    ViolationType | ""
  >("");

  const [
    selectedStatus,
    setSelectedStatus,
  ] = useState<
    ReviewStatus | ""
  >("");

  const [
    searchValue,
    setSearchValue,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );


  const [
    lastUpdatedLabel,
    setLastUpdatedLabel,
  ] = useState<string | null>(
    null,
  );

  const [
    currentPage,
    setCurrentPage,
  ] = useState(1);

  const [
    pageSize,
    setPageSize,
  ] = useState(10);

  const requestInFlightRef =
    useRef(false);

  const camerasById = useMemo(
    () =>
      new Map(
        cameras.map((camera) => [
          camera.id,
          camera,
        ]),
      ),
    [cameras],
  );

  const videosById = useMemo(
    () =>
      new Map(
        videos.map((video) => [
          video.id,
          video,
        ]),
      ),
    [videos],
  );

  const filteredViolations =
    useMemo(() => {
      const normalizedSearch =
        searchValue
          .trim()
          .toLowerCase();

      if (!normalizedSearch) {
        return response.items;
      }

      return response.items.filter(
        (violation) => {
          const camera =
            violation.camera_id
              ? camerasById.get(
                  violation.camera_id,
                )
              : undefined;

          const video =
            videosById.get(
              violation.video_id,
            );

          const searchableContent = [
            violation.violation_type,
            violation.review_status,
            violation.track_id,
            violation.license_plate,
            camera?.name,
            camera?.location,
            video?.original_filename,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();

          return searchableContent.includes(
            normalizedSearch,
          );
        },
      );
    }, [
      response.items,
      searchValue,
      camerasById,
      videosById,
    ]);

  const totalPages =
    Math.max(
      1,
      Math.ceil(
        filteredViolations.length /
          pageSize,
      ),
    );

  const safeCurrentPage =
    Math.min(
      currentPage,
      totalPages,
    );

  const pageStartIndex =
    (
      safeCurrentPage - 1
    ) * pageSize;

  const pageEndIndex =
    Math.min(
      pageStartIndex +
        pageSize,
      filteredViolations.length,
    );

  const paginatedViolations =
    filteredViolations.slice(
      pageStartIndex,
      pageEndIndex,
    );

  const firstVisibleItem =
    filteredViolations.length
      ? pageStartIndex + 1
      : 0;

  const lastVisibleItem =
    filteredViolations.length
      ? pageEndIndex
      : 0;

  const loadViolations =
    useCallback(async () => {
      if (
        requestInFlightRef.current
      ) {
        return;
      }

      requestInFlightRef.current =
        true;

      setLoading(true);
      setError(null);

      try {
        const nextResponse =
          await getViolations({
            limit: 100,
            violationType:
              selectedType || undefined,
            reviewStatus:
              selectedStatus || undefined,
          });

        setResponse(
          nextResponse,
        );

        setCurrentPage(1);

        setLastUpdatedLabel(
          createUpdatedTimeLabel(),
        );
      } catch (
        requestError
      ) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Violations could not be loaded.",
        );
      } finally {
        requestInFlightRef.current =
          false;

        setLoading(false);
      }
    }, [
      selectedStatus,
      selectedType,
    ]);

  useEffect(() => {
    function refreshWhenVisible() {
      if (
        document.visibilityState ===
        "visible"
      ) {
        void loadViolations();
      }
    }

    const intervalId =
      window.setInterval(
        refreshWhenVisible,
        5000,
      );

    document.addEventListener(
      "visibilitychange",
      refreshWhenVisible,
    );

    return () => {
      window.clearInterval(
        intervalId,
      );

      document.removeEventListener(
        "visibilitychange",
        refreshWhenVisible,
      );
    };
  }, [
    loadViolations,
  ]);

  function clearFilters() {
    setSelectedType("");
    setSelectedStatus("");
    setSearchValue("");
    setCurrentPage(1);
  }

  const pendingCount =
    response.items.filter(
      (item) =>
        item.review_status === "pending",
    ).length;

  const confirmedCount =
    response.items.filter(
      (item) =>
        item.review_status ===
        "confirmed",
    ).length;

  const rejectedCount =
    response.items.filter(
      (item) =>
        item.review_status ===
        "rejected",
    ).length;

  return (
    <div>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <ShieldAlert
            size={21}
            className="text-cyan-700"
          />

          <p className="mt-4 text-sm text-slate-500">
            Total violations
          </p>

          <p className="mt-1 text-2xl font-bold text-slate-950">
            {response.total}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <Clock3
            size={21}
            className="text-amber-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Pending review
          </p>

          <p className="mt-1 text-2xl font-bold text-slate-950">
            {pendingCount}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <CheckCircle2
            size={21}
            className="text-emerald-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Confirmed
          </p>

          <p className="mt-1 text-2xl font-bold text-slate-950">
            {confirmedCount}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <XCircle
            size={21}
            className="text-rose-600"
          />

          <p className="mt-4 text-sm text-slate-500">
            Rejected
          </p>

          <p className="mt-1 text-2xl font-bold text-slate-950">
            {rejectedCount}
          </p>
        </article>
      </section>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <Filter
              size={19}
              className="text-cyan-700"
            />

            <h2 className="font-semibold text-slate-950">
              Filter violations
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />

            <span>
              Live refresh every 5 seconds
            </span>

            <span className="text-slate-300">
              •
            </span>

            <span>
              {lastUpdatedLabel
                ? `Updated ${lastUpdatedLabel}`
                : "Waiting for refresh"}
            </span>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-[1fr_220px_220px_auto]">
          <label className="relative">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              value={searchValue}
              onChange={(event) => {
                setSearchValue(
                  event.target.value,
                );

                setCurrentPage(1);
              }}
              placeholder="Search camera, video, track or plate"
              className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 text-sm outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
            />
          </label>

          <select
            value={selectedType}
            onChange={(event) => {
              setSelectedType(
                event.target.value as
                  | ViolationType
                  | "",
              );

              setCurrentPage(1);
            }}
            className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-cyan-400"
          >
            <option value="">
              All violation types
            </option>

            {violationTypes.map(
              (type) => (
                <option
                  key={type.value}
                  value={type.value}
                >
                  {type.label}
                </option>
              ),
            )}
          </select>

          <select
            value={selectedStatus}
            onChange={(event) => {
              setSelectedStatus(
                event.target.value as
                  | ReviewStatus
                  | "",
              );

              setCurrentPage(1);
            }}
            className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-cyan-400"
          >
            <option value="">
              All review statuses
            </option>

            {reviewStatuses.map(
              (status) => (
                <option
                  key={status.value}
                  value={status.value}
                >
                  {status.label}
                </option>
              ),
            )}
          </select>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={loadViolations}
              disabled={loading}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-5 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw
                size={17}
                className={
                  loading
                    ? "animate-spin"
                    : ""
                }
              />

              Apply
            </button>

            <button
              type="button"
              onClick={clearFilters}
              className="h-11 w-full rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-600 lg:w-auto hover:bg-slate-50"
            >
              Clear
            </button>
          </div>
        </div>

        {error ? (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <AlertCircle size={18} />
            {error}
          </div>
        ) : null}
      </section>

      <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {filteredViolations.length ? (
          <>
          <MobileTableNotice />

          <div className="overflow-x-auto overscroll-x-contain touch-pan-x [scrollbar-width:thin]">
            <table className="w-full min-w-[1050px] text-left">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-4">
                    Violation
                  </th>

                  <th className="px-5 py-4">
                    Camera
                  </th>

                  <th className="px-5 py-4">
                    Video
                  </th>

                  <th className="px-5 py-4">
                    Confidence
                  </th>

                  <th className="px-5 py-4">
                    Review
                  </th>

                  <th className="px-5 py-4">
                    Occurred
                  </th>

                  <th className="px-5 py-4 text-right">
                    Action
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {paginatedViolations.map(
                  (violation) => {
                    const camera =
                      violation.camera_id
                        ? camerasById.get(
                            violation.camera_id,
                          )
                        : undefined;

                    const video =
                      videosById.get(
                        violation.video_id,
                      );

                    const confidence =
                      getConfidence(
                        violation,
                      );

                    const StatusIcon =
                      statusIcons[
                        violation
                          .review_status
                      ];

                    return (
                      <tr
                        key={violation.id}
                        className="hover:bg-slate-50/70"
                      >
                        <td className="px-5 py-4">
                          <p className="text-sm font-semibold text-slate-950">
                            {formatLabel(
                              violation
                                .violation_type,
                            )}
                          </p>

                          <p className="mt-1 text-xs text-slate-400">
                            Track{" "}
                            {violation.track_id ??
                              "Not available"}
                          </p>
                        </td>

                        <td className="px-5 py-4">
                          <p className="text-sm font-medium text-slate-700">
                            {camera?.name ??
                              "Unassigned"}
                          </p>

                          <p className="mt-1 text-xs text-slate-400">
                            {camera?.location ??
                              "No location"}
                          </p>
                        </td>

                        <td className="px-5 py-4">
                          <p className="max-w-[220px] truncate text-sm text-slate-700">
                            {video?.original_filename ??
                              "Unknown video"}
                          </p>
                        </td>

                        <td className="px-5 py-4">
                          <span className="text-sm font-semibold text-cyan-700">
                            {confidence ===
                            null
                              ? "—"
                              : `${Math.round(
                                  confidence *
                                    100,
                                )}%`}
                          </span>
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={[
                              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
                              statusStyles[
                                violation
                                  .review_status
                              ],
                            ].join(" ")}
                          >
                            <StatusIcon
                              size={14}
                            />

                            {formatLabel(
                              violation
                                .review_status,
                            )}
                          </span>
                        </td>

                        <td className="px-5 py-4 text-sm text-slate-500">
                          {formatDate(
                            violation.occurred_at,
                          )}
                        </td>

                        <td className="px-5 py-4 text-right">
                          <Link
                            href={`/violations/${violation.id}`}
                            className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm font-semibold text-slate-700 hover:border-cyan-300 hover:bg-cyan-50 hover:text-cyan-800"
                          >
                            <Eye size={16} />
                            Review
                          </Link>
                        </td>
                      </tr>
                    );
                  },
                )}
              </tbody>
            </table>
          </div>
          </>
        ) : (
          <div className="px-6 py-16 text-center">
            <ShieldAlert
              size={36}
              className="mx-auto text-slate-300"
            />

            <h3 className="mt-4 font-semibold text-slate-950">
              No violations found
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              No violations match the current
              filters.
            </p>
          </div>
        )}

        {filteredViolations.length ? (
          <PaginationControls
            currentPage={
              safeCurrentPage
            }
            totalPages={
              totalPages
            }
            pageSize={
              pageSize
            }
            totalItems={
              filteredViolations.length
            }
            startItem={
              firstVisibleItem
            }
            endItem={
              lastVisibleItem
            }
            disabled={
              loading
            }
            onPageChange={
              setCurrentPage
            }
            onPageSizeChange={(
              nextPageSize,
            ) => {
              setPageSize(
                nextPageSize,
              );

              setCurrentPage(1);
            }}
          />
        ) : null}
      </section>
    </div>
  );
}
