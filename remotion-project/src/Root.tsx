import React from "react";
import { Composition } from "remotion";
import { EditOverlay, EditProps } from "./Composition";
import { brand } from "./brand";

const defaultProps: EditProps = {
  segments: [
    { start: 0.2, end: 3.3, text: "Nằm sàn mát nhất nhà" },
    { start: 3.7, end: 6.8, text: "Đi theo chủ như cái bóng" },
    { start: 7.2, end: 10.3, text: "Selfie: lại gần một chút..." },
    { start: 10.7, end: 13.8, text: "Hộp mới là nhà mới" },
  ],
  lowerThird: { title: "Meo Cookie", subtitle: "IMEJI日本語教室", startSec: 0.5, durationSec: 3.5 },
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="EditOverlay"
    component={EditOverlay}
    durationInFrames={brand.export.fps * 14}
    fps={brand.export.fps}
    width={1080}
    height={1920}
    defaultProps={defaultProps}
  />
);
