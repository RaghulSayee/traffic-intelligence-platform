"use client";

import {
  AlertTriangle,
  Check,
  CheckCircle2,
  CircleOff,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import {
  useMemo,
} from "react";

import {
  getEnabledSceneReadiness,
} from "@/lib/cameras/scene-readiness";
import type {
  SceneRequirementStatus,
} from "@/lib/cameras/scene-readiness";
import type {
  CameraSceneConfiguration,
} from "@/types/camera-scene";

type SceneReadinessPanelProps = {
  scene: CameraSceneConfiguration;
};

const requirementStyles: Record<
  SceneRequirementStatus,
  {
    icon: typeof Check;
    iconClassName: string;
    containerClassName: string;
  }
> = {
  pass: {
    icon: Check,
    iconClassName:
      "text-emerald-600",
    containerClassName:
      "border-emerald-100 bg-emerald-50/60",
  },

  warning: {
    icon: AlertTriangle,
    iconClassName:
      "text-amber-600",
    containerClassName:
      "border-amber-100 bg-amber-50/60",
  },

  fail: {
    icon: XCircle,
    iconClassName:
      "text-rose-600",
    containerClassName:
      "border-rose-100 bg-rose-50/60",
  },
};

export function SceneReadinessPanel({
  scene,
}: SceneReadinessPanelProps) {
  const enabledRules =
    useMemo(
      () =>
        getEnabledSceneReadiness(
          scene,
        ),
      [scene],
    );

  const readyCount =
    enabledRules.filter(
      (rule) => rule.ready,
    ).length;

  const blockedCount =
    enabledRules.length -
    readyCount;

  const allReady =
    enabledRules.length > 0 &&
    blockedCount === 0;

  return (
    <section
      className={[
        "rounded-2xl border p-5 shadow-sm",
        allReady
          ? "border-emerald-200 bg-emerald-50/30"
          : blockedCount > 0
            ? "border-amber-200 bg-amber-50/20"
            : "border-slate-200 bg-white",
      ].join(" ")}
    >
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div className="flex items-start gap-3">
          <span
            className={[
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl",
              allReady
                ? "bg-emerald-100 text-emerald-700"
                : blockedCount > 0
                  ? "bg-amber-100 text-amber-700"
                  : "bg-slate-100 text-slate-600",
            ].join(" ")}
          >
            {allReady ? (
              <ShieldCheck
                size={22}
              />
            ) : (
              <ShieldAlert
                size={22}
              />
            )}
          </span>

          <div>
            <h2 className="font-semibold text-slate-950">
              Scene readiness
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Checks whether each enabled
              violation has the required scene
              geometry and relationships.
            </p>
          </div>
        </div>

        {enabledRules.length ? (
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-700">
              <CheckCircle2
                size={14}
              />

              {readyCount} ready
            </span>

            {blockedCount > 0 ? (
              <span className="inline-flex items-center gap-2 rounded-full bg-rose-100 px-3 py-1.5 text-xs font-semibold text-rose-700">
                <CircleOff
                  size={14}
                />

                {blockedCount} blocked
              </span>
            ) : null}
          </div>
        ) : null}
      </div>

      {!enabledRules.length ? (
        <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-white px-5 py-8 text-center">
          <ShieldAlert
            size={30}
            className="mx-auto text-slate-300"
          />

          <h3 className="mt-3 text-sm font-semibold text-slate-800">
            No violation rules enabled
          </h3>

          <p className="mt-1 text-sm text-slate-500">
            Select at least one rule from the
            Enabled Violations panel.
          </p>
        </div>
      ) : (
        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          {enabledRules.map(
            (rule) => (
              <article
                key={
                  rule.violationType
                }
                className="rounded-xl border border-slate-200 bg-white p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-950">
                      {rule.label}
                    </p>

                    <p className="mt-1 text-xs text-slate-400">
                      {
                        rule.requirements
                          .length
                      }{" "}
                      readiness checks
                    </p>
                  </div>

                  <span
                    className={[
                      "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
                      rule.ready
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-rose-50 text-rose-700",
                    ].join(" ")}
                  >
                    {rule.ready ? (
                      <CheckCircle2
                        size={14}
                      />
                    ) : (
                      <XCircle
                        size={14}
                      />
                    )}

                    {rule.ready
                      ? "Ready"
                      : "Needs setup"}
                  </span>
                </div>

                <div className="mt-4 space-y-2">
                  {rule.requirements.map(
                    (requirement) => {
                      const style =
                        requirementStyles[
                          requirement
                            .status
                        ];

                      const Icon =
                        style.icon;

                      return (
                        <div
                          key={
                            requirement.id
                          }
                          className={[
                            "flex items-start gap-3 rounded-lg border px-3 py-3",
                            style.containerClassName,
                          ].join(" ")}
                        >
                          <Icon
                            size={16}
                            className={[
                              "mt-0.5 shrink-0",
                              style.iconClassName,
                            ].join(" ")}
                          />

                          <div>
                            <p className="text-xs font-semibold text-slate-800">
                              {
                                requirement.label
                              }
                            </p>

                            <p className="mt-1 text-xs leading-5 text-slate-500">
                              {
                                requirement.detail
                              }
                            </p>
                          </div>
                        </div>
                      );
                    },
                  )}
                </div>
              </article>
            ),
          )}
        </div>
      )}
    </section>
  );
}
