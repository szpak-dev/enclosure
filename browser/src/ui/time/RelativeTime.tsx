import { useSyncExternalStore, type ReactElement } from "react";

enum RelativeTimeClockStatus {
  Idle = "idle",
  Running = "running",
}

type RelativeTimeClockState =
  | Readonly<{ status: RelativeTimeClockStatus.Idle }>
  | Readonly<{
      intervalId: number;
      status: RelativeTimeClockStatus.Running;
    }>;

class RelativeTimeClock {
  private readonly formatter = new Intl.RelativeTimeFormat("en", {
    numeric: "always",
  });
  private readonly listeners = new Set<() => void>();
  private now = Date.now();
  private state: RelativeTimeClockState = {
    status: RelativeTimeClockStatus.Idle,
  };

  readonly getSnapshot = (): number => this.now;

  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    if (this.state.status === RelativeTimeClockStatus.Idle) {
      this.now = Date.now();
      this.state = {
        intervalId: window.setInterval(() => {
          this.now = Date.now();
          this.listeners.forEach((current) => current());
        }, 60_000),
        status: RelativeTimeClockStatus.Running,
      };
    }

    return () => {
      this.listeners.delete(listener);
      if (
        this.listeners.size === 0 &&
        this.state.status === RelativeTimeClockStatus.Running
      ) {
        window.clearInterval(this.state.intervalId);
        this.state = { status: RelativeTimeClockStatus.Idle };
      }
    };
  };

  format(timestamp: string, now: number): string {
    const difference = Date.parse(timestamp) - now;
    const magnitude = Math.abs(difference);

    if (magnitude < 60_000)
      return difference > 0
        ? "in less than a minute"
        : "less than a minute ago";
    if (magnitude < 3_600_000)
      return this.formatter.format(Math.round(difference / 60_000), "minute");
    if (magnitude < 86_400_000)
      return this.formatter.format(Math.round(difference / 3_600_000), "hour");
    if (magnitude < 604_800_000)
      return this.formatter.format(Math.round(difference / 86_400_000), "day");
    if (magnitude < 2_629_800_000)
      return this.formatter.format(
        Math.round(difference / 604_800_000),
        "week",
      );
    if (magnitude < 31_557_600_000)
      return this.formatter.format(
        Math.round(difference / 2_629_800_000),
        "month",
      );
    return this.formatter.format(
      Math.round(difference / 31_557_600_000),
      "year",
    );
  }
}

const relativeTimeClock = new RelativeTimeClock();

export type RelativeTimeProps = {
  prefix?: string;
  timestamp: string;
};

export function useRelativeTime(timestamp: string): string {
  const now = useSyncExternalStore(
    relativeTimeClock.subscribe,
    relativeTimeClock.getSnapshot,
    relativeTimeClock.getSnapshot,
  );
  return relativeTimeClock.format(timestamp, now);
}

export function RelativeTime({
  prefix = "",
  timestamp,
}: RelativeTimeProps): ReactElement {
  const relativeTime = useRelativeTime(timestamp);

  return (
    <time dateTime={timestamp} title={timestamp}>
      {prefix}
      {relativeTime}
    </time>
  );
}
