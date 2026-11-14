import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { brand } from "../brand";

export const LowerThird: React.FC<{
  title: string;
  subtitle?: string;
  startSec?: number;
  durationSec?: number;
}> = ({ title, subtitle, startSec = 0.5, durationSec = 4 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const start = startSec * fps;
  const end = (startSec + durationSec) * fps;

  const inP = spring({ frame: frame - start, fps, config: { damping: 200 } });
  const outP = spring({ frame: frame - end, fps, config: { damping: 200 } });
  const p = inP - outP;
  if (p <= 0.001) return null;

  const x = interpolate(p, [0, 1], [-80, 0]);

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-start", padding: "0 0 460px 60px" }}>
      <div
        style={{
          opacity: p,
          transform: `translateX(${x}px)`,
          display: "flex",
          overflow: "hidden",
          borderRadius: brand.radius.lg,
          boxShadow: brand.shadow.pop,
          background: brand.color.white,
          fontFamily: brand.font.sans,
        }}
      >
        <div style={{ width: 14, background: brand.color.primary }} />
        <div style={{ padding: "18px 36px 18px 28px" }}>
          <div style={{ fontSize: 44, fontWeight: 800, color: brand.color.text, lineHeight: 1.15 }}>{title}</div>
          {subtitle ? (
            <div style={{ fontSize: 28, fontWeight: 500, color: brand.color.primary, marginTop: 6 }}>{subtitle}</div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
