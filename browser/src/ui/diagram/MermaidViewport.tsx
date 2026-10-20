import { ActionIcon, Box, Group, Paper, Text, Tooltip } from "@mantine/core";
import {
  IconFocusCentered,
  IconZoomIn,
  IconZoomOut,
} from "@tabler/icons-react";
import {
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type RefObject,
  type WheelEvent,
} from "react";

type MermaidViewportProps = {
  host: RefObject<HTMLDivElement | null>;
  ready: boolean;
  title: string;
};

type ViewTransform = {
  scale: number;
  x: number;
  y: number;
};

type Drag = {
  pointerId: number;
  x: number;
  y: number;
};

const initialTransform: ViewTransform = { scale: 1, x: 0, y: 0 };
const minimumScale = 0.2;
const maximumScale = 12;
const zoomFactor = 1.25;

function boundedScale(scale: number): number {
  return Math.min(maximumScale, Math.max(minimumScale, scale));
}

export function MermaidViewport({ host, ready, title }: MermaidViewportProps) {
  const viewport = useRef<HTMLDivElement>(null);
  const drag = useRef<Drag | undefined>(undefined);
  const [dragging, setDragging] = useState(false);
  const [transform, setTransform] = useState(initialTransform);

  const reset = () => setTransform(initialTransform);
  const zoomAtCenter = (factor: number) => {
    setTransform((current) => {
      const scale = boundedScale(current.scale * factor);
      const ratio = scale / current.scale;
      return { scale, x: current.x * ratio, y: current.y * ratio };
    });
  };
  const panBy = (x: number, y: number) => {
    setTransform((current) => ({
      ...current,
      x: current.x + x,
      y: current.y + y,
    }));
  };
  const handleWheel = (event: WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    const bounds = viewport.current?.getBoundingClientRect();
    if (!bounds) return;

    const pointX = event.clientX - bounds.left - bounds.width / 2;
    const pointY = event.clientY - bounds.top - bounds.height / 2;
    const factor = event.deltaY < 0 ? zoomFactor : 1 / zoomFactor;
    setTransform((current) => {
      const scale = boundedScale(current.scale * factor);
      const ratio = scale / current.scale;
      return {
        scale,
        x: pointX - (pointX - current.x) * ratio,
        y: pointY - (pointY - current.y) * ratio,
      };
    });
  };
  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (!ready || event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
    };
    setDragging(true);
  };
  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (drag.current?.pointerId !== event.pointerId) return;
    const movementX = event.clientX - drag.current.x;
    const movementY = event.clientY - drag.current.y;
    drag.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
    };
    panBy(movementX, movementY);
  };
  const finishDrag = (event: PointerEvent<HTMLDivElement>) => {
    if (drag.current?.pointerId !== event.pointerId) return;
    drag.current = undefined;
    setDragging(false);
    event.currentTarget.releasePointerCapture(event.pointerId);
  };
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const actions: Partial<Record<string, () => void>> = {
      "+": () => zoomAtCenter(zoomFactor),
      "-": () => zoomAtCenter(1 / zoomFactor),
      "0": reset,
      "=": () => zoomAtCenter(zoomFactor),
      ArrowDown: () => panBy(0, -40),
      ArrowLeft: () => panBy(40, 0),
      ArrowRight: () => panBy(-40, 0),
      ArrowUp: () => panBy(0, 40),
    };
    const action = actions[event.key];
    if (!action) return;
    event.preventDefault();
    action();
  };

  return (
    <Box h="100%" pos="relative" w="100%">
      {ready ? (
        <>
          <Paper
            p={4}
            pos="absolute"
            shadow="sm"
            withBorder
            style={{
              left: "var(--mantine-spacing-sm)",
              top: "var(--mantine-spacing-sm)",
              zIndex: 2,
            }}
          >
            <Tooltip label="Center and fit diagram">
              <ActionIcon
                aria-label="Center and fit diagram"
                onClick={reset}
                variant="default"
              >
                <IconFocusCentered aria-hidden size={18} />
              </ActionIcon>
            </Tooltip>
          </Paper>
          <Paper
            aria-label="Diagram zoom controls"
            p={4}
            pos="absolute"
            role="toolbar"
            shadow="sm"
            withBorder
            style={{
              right: "var(--mantine-spacing-sm)",
              top: "var(--mantine-spacing-sm)",
              zIndex: 2,
            }}
          >
            <Group gap={4}>
              <Tooltip label="Zoom out">
                <ActionIcon
                  aria-label="Zoom out"
                  disabled={transform.scale <= minimumScale}
                  onClick={() => zoomAtCenter(1 / zoomFactor)}
                  variant="default"
                >
                  <IconZoomOut aria-hidden size={18} />
                </ActionIcon>
              </Tooltip>
              <Text aria-label="Zoom level" miw={42} size="xs" ta="center">
                {Math.round(transform.scale * 100)}%
              </Text>
              <Tooltip label="Zoom in">
                <ActionIcon
                  aria-label="Zoom in"
                  disabled={transform.scale >= maximumScale}
                  onClick={() => zoomAtCenter(zoomFactor)}
                  variant="default"
                >
                  <IconZoomIn aria-hidden size={18} />
                </ActionIcon>
              </Tooltip>
            </Group>
          </Paper>
        </>
      ) : null}
      <Box
        aria-hidden={!ready}
        aria-label={`${title} Mermaid preview`}
        h="100%"
        onDoubleClick={reset}
        onKeyDown={handleKeyDown}
        onPointerCancel={finishDrag}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishDrag}
        onWheel={handleWheel}
        ref={viewport}
        role="img"
        tabIndex={ready ? 0 : -1}
        style={{
          backgroundColor: "var(--mantine-color-body)",
          backgroundImage:
            "radial-gradient(circle, var(--mantine-color-default-border) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
          cursor: ready ? (dragging ? "grabbing" : "grab") : "default",
          overflow: "hidden",
          touchAction: "none",
        }}
      >
        <Box
          h="100%"
          ref={host}
          style={{
            transform: `translate3d(${transform.x}px, ${transform.y}px, 0) scale(${transform.scale})`,
            transformOrigin: "center center",
          }}
        />
      </Box>
    </Box>
  );
}
