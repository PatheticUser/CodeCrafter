"use client";

import { useEffect, useRef } from "react";
import { wsUrlFor, type AgentEvent, type AgentEventType } from "@/lib/codecrafter";

/**
 * Subscribes to an agent run's event stream.
 *
 * - Replays persisted events (`?since=` protocol) from last received sequence.
 * - Reconnects automatically while the run is still active.
 * - Detaches safely on unmount; the backend run keeps going either way.
 */
export function useRunEvents(
  runId: string | null,
  onEvent: (event: AgentEvent) => void,
  onClosed?: (terminal?: boolean) => void
) {
  const eventRef = useRef(onEvent);
  const closedRef = useRef(onClosed);
  eventRef.current = onEvent;
  closedRef.current = onClosed;

  const lastSeqRef = useRef(0);

  useEffect(() => {
    if (!runId) return;

    lastSeqRef.current = 0;
    let cancelled = false;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempts = 0;

    const connect = () => {
      if (cancelled) return;
      const url = `${wsUrlFor(`/api/agent/runs/${runId}/events`)}?since=${lastSeqRef.current}`;
      ws = new WebSocket(url);

      ws.onmessage = (msg) => {
        try {
          const ev = JSON.parse(msg.data as string) as AgentEvent;
          if (typeof ev.sequence === "number" && ev.sequence > lastSeqRef.current) {
            lastSeqRef.current = ev.sequence;
          }
          eventRef.current(ev);
          if (isTerminal(ev.type)) {
            if (cancelled) return;
            closedRef.current?.(true);
            // stop reconnecting on terminal event
            cancelled = true;
            ws?.close();
          }
        } catch {
          /* ignore malformed frames */
        }
      };

      ws.onclose = () => {
        if (cancelled) return;
        // Run may have finished while connected — query the run endpoint.
        attempts += 1;
        if (attempts <= 10) {
          reconnectTimer = setTimeout(connect, Math.min(1000 * attempts, 4000));
          closedRef.current?.(false);
        } else {
          closedRef.current?.(false);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [runId]);
}

const TERMINAL_EVENTS: AgentEventType[] = ["agent.completed", "agent.failed", "agent.cancelled"];

export function isTerminal(type: AgentEventType): boolean {
  return TERMINAL_EVENTS.includes(type);
}
