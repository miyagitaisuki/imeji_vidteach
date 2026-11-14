import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { brand } from "../brand";

// Định dạng khớp đầu ra của `whisper --output_format json` (segments[])
export type Segment = { start: number; end: number; text: string };

export const Subtitles: React.FC<{ segments: Segment[]; bottom?: number }> = ({ segments, bottom = 300 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const seg = segments.find((s) => t >= s.start && t < s.end);
  if (!seg) return null;

  const fadeIn = Math.min(1, (t - seg.start) / 0.12);
  const fadeOut = Math.min(1, (seg.end - t) / 0.12);
  const o = Math.max(0, Math.min(fadeIn, fadeOut));

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: bottom }}>
      <div
        style={{
          opacity: o,
          transform: `translateY(${(1 - o) * 8}px)`,
          maxWidth: 940,
          padding: "14px 32px",
          borderRadius: brand.radius.lg,
          background: "rgba(15,23,42,0.82)",
          color: brand.color.white,
          fontFamily: brand.font.sans,
          fontSize: 48,
          lineHeight: 1.3,
          fontWeight: 600,
          textAlign: "center",
          boxShadow: brand.shadow.pop,
        }}
      >
        {seg.text.trim()}
      </div>
    </AbsoluteFill>
  );
};
