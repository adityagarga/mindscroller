// Tiny FLIP-technique hook so list items animate up/down when their order
// changes. Keyed by a stable string id (e.g. category name) so React can
// remount/move rows freely while we still recognise "this is the same row".
//
// Usage:
//   const ref = useFlipReorder(category.name);
//   return <div ref={ref}>...</div>
//
// We measure `offsetTop` (the element's layout position within its
// offsetParent) rather than `getBoundingClientRect().top` (viewport-relative).
// This means scrolling an ancestor doesn't change the measurement, so the
// animation only fires when the row's actual layout order changes — not on
// every scroll event.

import { useLayoutEffect, useRef } from "react";

// Module-level so the previous-frame position survives the React commit.
const lastOffsetByKey = new Map<string, number>();

export function useFlipReorder<T extends HTMLElement = HTMLDivElement>(key: string) {
  const ref = useRef<T | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const offset = el.offsetTop;
    const prevOffset = lastOffsetByKey.get(key);
    if (prevOffset != null && prevOffset !== offset) {
      const dy = prevOffset - offset;
      // The browser has already laid out at the new position. Counter it with
      // a transform and let it slide back to zero.
      el.animate(
        [
          { transform: `translateY(${dy}px)` },
          { transform: "translateY(0)" },
        ],
        { duration: 350, easing: "cubic-bezier(.2,.7,.2,1)" },
      );
    }
    lastOffsetByKey.set(key, offset);
  });

  return ref;
}
