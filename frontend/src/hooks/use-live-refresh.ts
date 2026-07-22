"use client";

import {
  useRouter,
} from "next/navigation";
import {
  useCallback,
  useEffect,
  useState,
  useSyncExternalStore,
  useTransition,
} from "react";

type UseLiveRefreshOptions = {
  enabled?: boolean;
  intervalMs?: number;
};

function subscribeToVisibility(
  callback: () => void,
): () => void {
  document.addEventListener(
    "visibilitychange",
    callback,
  );

  return () => {
    document.removeEventListener(
      "visibilitychange",
      callback,
    );
  };
}

function getVisibilitySnapshot(): boolean {
  return (
    document.visibilityState ===
    "visible"
  );
}

function getServerVisibilitySnapshot(): boolean {
  return true;
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

export function useLiveRefresh({
  enabled = true,
  intervalMs = 5000,
}: UseLiveRefreshOptions = {}) {
  const router = useRouter();

  const [
    isRefreshing,
    startRefresh,
  ] = useTransition();

  /*
   * Keep this null during server rendering and
   * initial browser hydration.
   */
  const [
    lastUpdatedLabel,
    setLastUpdatedLabel,
  ] = useState<string | null>(
    null,
  );

  const isPageVisible =
    useSyncExternalStore(
      subscribeToVisibility,
      getVisibilitySnapshot,
      getServerVisibilitySnapshot,
    );

  const refresh =
    useCallback(() => {
      startRefresh(() => {
        router.refresh();

        setLastUpdatedLabel(
          createUpdatedTimeLabel(),
        );
      });
    }, [
      router,
      startRefresh,
    ]);

  useEffect(() => {
    if (
      !enabled ||
      !isPageVisible
    ) {
      return;
    }

    const intervalId =
      window.setInterval(
        refresh,
        intervalMs,
      );

    return () => {
      window.clearInterval(
        intervalId,
      );
    };
  }, [
    enabled,
    intervalMs,
    isPageVisible,
    refresh,
  ]);

  useEffect(() => {
    function handleVisibilityChange() {
      if (
        enabled &&
        document.visibilityState ===
          "visible"
      ) {
        refresh();
      }
    }

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange,
    );

    return () => {
      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange,
      );
    };
  }, [
    enabled,
    refresh,
  ]);

  return {
    refresh,
    isRefreshing,
    lastUpdatedLabel,
    isPageVisible,
  };
}
