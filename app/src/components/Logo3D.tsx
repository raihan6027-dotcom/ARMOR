import s from "./intro.module.css";

/** The ARMOR mark as stacked layers with a light sheen masked to the logo shape. */
export function Logo3D({ mode }: { mode: "spin" | "float" }) {
  const depth = mode === "spin" ? [10, 8, 6, 4, 2] : [14, 12, 10, 8, 6, 4, 2];
  return (
    <div className={mode === "spin" ? s.persp : s.perspBig}>
      <div className={`${s.layers} ${mode === "spin" ? s.spinIn : s.tilt}`}>
        {depth.map((z, i) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={z}
            aria-hidden="true"
            alt=""
            src="/armor-mark.png"
            className={s.layer}
            style={{
              transform: `translateZ(-${z}px)`,
              filter: `brightness(${0.22 + (i * 0.3) / depth.length})`,
            }}
          />
        ))}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="Logo ARMOR" src="/armor-mark.png" className={s.layer} />
        <div aria-hidden="true" className={`${s.mask} ${mode === "spin" ? s.sheenOnce : s.sheen}`} />
      </div>
    </div>
  );
}

/** Generic line face with landmarks; never a real person. */
export function FaceLines({ scanning }: { scanning: boolean }) {
  const dots: [number, number, number][] = [
    [100, 20, 2.6], [35, 120, 2.6], [165, 120, 2.6], [70, 110, 3], [130, 110, 3], [56, 96, 2.2],
    [86, 96, 2.2], [114, 96, 2.2], [144, 96, 2.2], [100, 146, 3], [93, 146, 2], [107, 146, 2],
    [78, 172, 2.6], [122, 172, 2.6], [100, 178, 2.2], [60, 190, 2.6], [140, 190, 2.6], [100, 215, 2.6],
  ];
  const line = { fill: "none", stroke: "var(--accent-soft)", strokeWidth: 1.5, strokeOpacity: 0.7 };
  return (
    <>
      <svg aria-hidden="true" viewBox="0 0 200 240" className={s.face}>
        <path className={s.draw} style={line} d="M100 20 C150 20 172 62 170 110 C168 160 140 205 100 215 C60 205 32 160 30 110 C28 62 50 20 100 20 Z" />
        <path className={s.draw} style={{ ...line, animationDelay: "0.2s" }} d="M56 96 Q70 88 86 96 M114 96 Q130 88 144 96" />
        <path className={s.draw} style={{ ...line, animationDelay: "0.3s" }} d="M58 110 Q70 102 82 110 Q70 116 58 110 Z M118 110 Q130 102 142 110 Q130 116 118 110 Z" />
        <path className={s.draw} style={{ ...line, animationDelay: "0.4s" }} d="M100 112 L93 146 L107 146 M78 172 Q100 184 122 172" />
        <path
          className={s.draw}
          style={{ fill: "none", stroke: "var(--accent)", strokeWidth: 0.75, strokeOpacity: 0.45, animationDelay: "0.6s" }}
          d="M70 110 L100 146 L130 110 M70 110 L78 172 M130 110 L122 172 M100 146 L78 172 M100 146 L122 172 M35 120 L70 110 M165 120 L130 110 M35 120 L60 190 M165 120 L140 190 M60 190 L100 215 L140 190 M78 172 L60 190 M122 172 L140 190"
        />
        {dots.map(([cx, cy, r], i) => (
          <circle key={`${cx}-${cy}`} className={s.pop} cx={cx} cy={cy} r={r} fill="var(--accent)" style={{ animationDelay: `${0.5 + i * 0.05}s` }} />
        ))}
      </svg>
      {scanning ? <div aria-hidden="true" className={s.beam} /> : null}
    </>
  );
}

export function ScanFrame({ ok, children }: { ok?: boolean; children: React.ReactNode }) {
  return (
    <div className={s.scanBox} style={{ ["--bracket" as string]: ok ? "var(--allow)" : "var(--accent)" }}>
      <div aria-hidden="true" className={`${s.corner} ${s.tl}`} />
      <div aria-hidden="true" className={`${s.corner} ${s.tr}`} />
      <div aria-hidden="true" className={`${s.corner} ${s.bl}`} />
      <div aria-hidden="true" className={`${s.corner} ${s.br}`} />
      {children}
    </div>
  );
}

export function ShieldCheck({ size = 40 }: { size?: number }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 28" width={size} height={size * 1.15}>
      <path d="M12 1 L22 5 V13 C22 20 17.5 25 12 27 C6.5 25 2 20 2 13 V5 Z" fill="rgba(95, 227, 177, 0.12)" stroke="var(--allow)" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M7.5 14 L10.8 17.2 L16.8 10.8" fill="none" stroke="var(--allow)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
