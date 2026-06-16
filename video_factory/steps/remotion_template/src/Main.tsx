import { Sequence, AbsoluteFill, staticFile, useCurrentFrame, interpolate } from "remotion";
import { Audio } from "@remotion/media";
import { Scene } from "./components/Scene";
import { SEGMENTS, BACKGROUNDS } from "./data";

const ProgressBar: React.FC<{ totalFrames: number }> = ({ totalFrames }) => {
  const frame = useCurrentFrame();
  const width = interpolate(frame, [0, totalFrames], [0, 100], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 34,
        left: 56,
        right: 56,
        height: 3,
        background: "rgba(255,255,255,0.13)",
        zIndex: 20,
      }}
    >
      <div
        style={{
          height: "100%",
          background: "rgba(255,255,255,0.68)",
          width: `${width}%`,
        }}
      />
    </div>
  );
};

export const MainScene: React.FC = () => {
  const starts = SEGMENTS.reduce<number[]>((acc, seg, i) => {
    acc.push(i === 0 ? 0 : acc[i - 1] + SEGMENTS[i - 1].duration_frames);
    return acc;
  }, []);
  const totalFrames = SEGMENTS.reduce((sum, seg) => sum + seg.duration_frames, 0);

  return (
    <AbsoluteFill style={{ background: "#080808" }}>
      {SEGMENTS.map((seg, i) => (
        <Sequence
          key={i}
          from={starts[i]}
          durationInFrames={seg.duration_frames}
          layout="none"
        >
          <Scene
            segment={seg}
            index={i}
            background={BACKGROUNDS[i % BACKGROUNDS.length]}
          />
          {seg.audio_path && (
            <Audio
              src={staticFile(
                seg.audio_path.replace(/\\/g, "/").split("/").pop() || ""
              )}
            />
          )}
        </Sequence>
      ))}
      <Sequence from={0} durationInFrames={totalFrames} layout="none">
        <ProgressBar totalFrames={totalFrames} />
      </Sequence>
    </AbsoluteFill>
  );
};
