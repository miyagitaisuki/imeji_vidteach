import React from "react";
import { AbsoluteFill } from "remotion";
import { Subtitles, Segment } from "./components/Subtitles";
import { LowerThird } from "./components/LowerThird";
import { loadBrandFonts } from "./fonts";
import { brand } from "./brand";

loadBrandFonts();

export type EditProps = {
  segments: Segment[];
  lowerThird: { title: string; subtitle?: string; startSec?: number; durationSec?: number };
};

// Lớp đồ hoạ trong suốt: render ProRes/WebM alpha rồi ffmpeg overlay lên video đã cắt,
// hoặc thêm <OffthreadVideo src=... /> bên dưới để render một lượt.
export const EditOverlay: React.FC<EditProps> = ({ segments, lowerThird }) => (
  <AbsoluteFill style={{ background: "transparent", color: brand.color.text }}>
    <LowerThird {...lowerThird} />
    <Subtitles segments={segments} />
    <div style={{ position: "absolute", top: 60, right: 50, fontFamily: brand.font.sans, fontSize: 24, color: "rgba(255,255,255,0.85)", textShadow: "0 1px 4px rgba(0,0,0,0.6)" }}>
      Music: Unheard - Void (freetouse.com)
    </div>
  </AbsoluteFill>
);
