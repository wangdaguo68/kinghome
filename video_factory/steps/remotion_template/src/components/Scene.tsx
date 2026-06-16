import { useCurrentFrame, useVideoConfig, interpolate, Easing, Img, staticFile } from "remotion";

interface Segment {
  narration: string;
  title: string;
  summary: string;
  source_label: string;
  heat_label: string;
  category: string;
  score: number | string;
  comments: number | string;
  image_path: string;
  audio_path: string;
  duration_seconds: number;
  duration_frames: number;
  caption_chunks: string[];
}

interface SceneProps {
  segment: Segment;
  index: number;
  background: string;
}

const activeCaption = (captions: string[], frame: number, durationFrames: number) => {
  if (!captions.length) {
    return "";
  }
  const paddedStart = Math.min(12, Math.floor(durationFrames * 0.08));
  const usable = Math.max(1, durationFrames - paddedStart - 8);
  const slot = usable / captions.length;
  const idx = Math.min(
    captions.length - 1,
    Math.max(0, Math.floor((frame - paddedStart) / slot))
  );
  return frame < paddedStart ? captions[0] : captions[idx];
};

export const Scene: React.FC<SceneProps> = ({ segment, index, background }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const caption = activeCaption(segment.caption_chunks, frame, segment.duration_frames);
  const imageFile = segment.image_path
    ? segment.image_path.replace(/\\/g, "/").split("/").pop() || ""
    : "";

  const fadeIn = interpolate(frame, [0, Math.round(0.4 * fps)], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const exitStart = Math.max(0, segment.duration_frames - Math.round(0.35 * fps));
  const opacity = interpolate(frame, [exitStart, segment.duration_frames], [1, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.in(Easing.ease),
  });
  const imageScale = interpolate(frame, [0, segment.duration_frames], [1.02, 1.07], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const captionY = interpolate(frame, [0, Math.round(0.35 * fps)], [18, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        opacity,
        background,
        fontFamily:
          'Inter, "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif',
      }}
    >
      {imageFile && (
        <Img
          src={staticFile(imageFile)}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${imageScale})`,
            filter: "saturate(0.82) contrast(0.96)",
          }}
        />
      )}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0.42) 0%, rgba(0,0,0,0.14) 42%, rgba(0,0,0,0.88) 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 58,
          left: 56,
          right: 56,
          opacity: fadeIn,
          color: "rgba(255,255,255,0.86)",
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 12,
            padding: "8px 12px",
            background: "rgba(0,0,0,0.38)",
            border: "1px solid rgba(255,255,255,0.14)",
            fontSize: 22,
            fontWeight: 600,
          }}
        >
          <span>{segment.source_label || "NEWS"}</span>
          <span style={{ opacity: 0.55 }}>/</span>
          <span>{segment.category || "快讯"}</span>
        </div>
      </div>
      {segment.title && (
        <div
          style={{
            position: "absolute",
            left: 56,
            right: 56,
            bottom: 330,
            color: "#fff",
            opacity: fadeIn,
            textShadow: "0 3px 22px rgba(0,0,0,0.9)",
          }}
        >
          <div
            style={{
              fontSize: 38,
              lineHeight: 1.18,
              fontWeight: 760,
              letterSpacing: 0,
            }}
          >
            {segment.title}
          </div>
          {segment.source_label && (
            <div
              style={{
                marginTop: 18,
                fontSize: 22,
                color: "rgba(255,255,255,0.74)",
                fontWeight: 500,
              }}
            >
              {[segment.source_label, segment.heat_label].filter(Boolean).join("  /  ")}
            </div>
          )}
          {segment.summary && (
            <div
              style={{
                marginTop: 22,
                padding: "18px 20px",
                background: "rgba(0,0,0,0.46)",
                borderLeft: "4px solid rgba(255,255,255,0.72)",
                color: "rgba(255,255,255,0.9)",
                fontSize: 27,
                lineHeight: 1.32,
                fontWeight: 560,
              }}
            >
              {segment.summary}
            </div>
          )}
        </div>
      )}
      <div
        style={{
          position: "absolute",
          left: 58,
          right: 58,
          bottom: 92,
          minHeight: 142,
          padding: "24px 30px",
          background: "rgba(0,0,0,0.74)",
          borderTop: "1px solid rgba(255,255,255,0.12)",
          color: "#fff",
          fontSize: 36,
          lineHeight: 1.32,
          fontWeight: 720,
          letterSpacing: 0,
          textShadow: "0 2px 12px rgba(0,0,0,0.85)",
          opacity: fadeIn,
          transform: `translateY(${captionY}px)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
        }}
      >
        {caption}
      </div>
    </div>
  );
};
