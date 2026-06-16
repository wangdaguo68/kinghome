import { Composition } from "remotion";
import { MainScene } from "./Main";
import { CONFIG, SEGMENTS } from "./data";

export const RemotionRoot: React.FC = () => {
  const durationInFrames = SEGMENTS.reduce((sum, seg) => sum + seg.duration_frames, 0);

  return (
    <>
      <Composition
        id="MainScene"
        component={MainScene}
        durationInFrames={durationInFrames}
        fps={CONFIG.fps}
        width={CONFIG.width}
        height={CONFIG.height}
      />
    </>
  );
};
