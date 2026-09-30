/** One consistent line icon set: 24px grid, 1.8px stroke, round caps and joins. */

const PATHS: Record<string, string> = {
  back: "M15 5l-7 7 7 7",
  close: "M6 6l12 12M18 6L6 18",
  check: "M5 12.5l4.5 4.5L19 7.5",
  cross: "M7 7l10 10M17 7L7 17",
  alert: "M12 4l9 16H3zM12 10v4.5M12 17.5v.5",
  home: "M4 11l8-7 8 7v8.5a.5.5 0 0 1-.5.5H15v-6H9v6H4.5a.5.5 0 0 1-.5-.5z",
  scan: "M4 9V5.5A1.5 1.5 0 0 1 5.5 4H9M15 4h3.5A1.5 1.5 0 0 1 20 5.5V9M20 15v3.5a1.5 1.5 0 0 1-1.5 1.5H15M9 20H5.5A1.5 1.5 0 0 1 4 18.5V15M4 12h16",
  inbox: "M4 13l2.5-7.5A1 1 0 0 1 7.5 5h9a1 1 0 0 1 1 .5L20 13v5.5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5zM4 13h5l1 2h4l1-2h5",
  shield: "M12 3l8 3.2V12c0 4.6-3.3 8.1-8 9-4.7-.9-8-4.4-8-9V6.2z",
  shieldCheck: "M12 3l8 3.2V12c0 4.6-3.3 8.1-8 9-4.7-.9-8-4.4-8-9V6.2zM8.5 12.2l2.4 2.4 4.6-4.8",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20c.8-3.6 3.8-6 7.5-6s6.7 2.4 7.5 6",
  lock: "M7 11V8a5 5 0 0 1 10 0v3M6 11h12v9H6zM12 14.5v2.5",
  unlock: "M7 11V8a5 5 0 0 1 9.6-2M6 11h12v9H6zM12 14.5v2.5",
  bell: "M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15zM10 20.5a2 2 0 0 0 4 0",
  chevron: "M9 5l7 7-7 7",
  replay: "M5 11a7 7 0 1 1 2 5M4 6.5V11h4.5",
  camera: "M4 8.5A1.5 1.5 0 0 1 5.5 7H8l1.5-2h5L16 7h2.5A1.5 1.5 0 0 1 20 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5zM12 16.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z",
  image: "M4 5.5A1.5 1.5 0 0 1 5.5 4h13A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5zM4 16l5-5 4 4 2.5-2.5L20 17M15.5 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2z",
  video: "M4 7.5A1.5 1.5 0 0 1 5.5 6h9A1.5 1.5 0 0 1 16 7.5v9a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 4 16.5zM16 10.5l4-2.5v8l-4-2.5",
  mic: "M12 4a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V7a3 3 0 0 1 3-3zM6 11.5a6 6 0 0 0 12 0M12 17.5V20",
  text: "M5 6h14M5 10h14M5 14h9M5 18h6",
  upload: "M12 16V5M7.5 9.5L12 5l4.5 4.5M5 16v2.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V16",
  download: "M12 5v11M7.5 11.5L12 16l4.5-4.5M5 16v2.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V16",
  trash: "M5 7h14M10 7V5h4v2M7 7l1 13h8l1-13M10.5 11v5.5M13.5 11v5.5",
  people: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM3 20c.6-3.2 3-5 6-5s5.4 1.8 6 5M16 4.5a3.5 3.5 0 0 1 0 6.5M17.5 14.5c1.9.6 3.1 2.2 3.5 5",
  chart: "M5 20V10M10 20V5M15 20v-7M20 20v-4",
  settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19 12l2-1.5-2-3.5-2.4.8a7 7 0 0 0-1.8-1L14.4 4h-4.8l-.4 2.8a7 7 0 0 0-1.8 1L5 7 3 10.5 5 12l-2 1.5L5 17l2.4-.8a7 7 0 0 0 1.8 1l.4 2.8h4.8l.4-2.8a7 7 0 0 0 1.8-1L19 17l2-3.5z",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v5.5M12 7.5v.5",
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2",
  key: "M14.5 9.5a4.5 4.5 0 1 0-4 4.47V20h3v-2h2v-2h-2v-2.03a4.5 4.5 0 0 0 1-6.47zM14.5 9.5h.01",
  logout: "M10 5H6.5A1.5 1.5 0 0 0 5 6.5v11A1.5 1.5 0 0 0 6.5 19H10M14.5 8l4 4-4 4M18.5 12H9",
  plus: "M12 5v14M5 12h14",
  wifiOff: "M3 3l18 18M8.5 16.5a5 5 0 0 1 7 0M5 12.5a10 10 0 0 1 4-2.3M19 12.5a10 10 0 0 0-3.4-2M12 20h.01",
};

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 22, title }: { name: IconName; size?: number; title?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
    >
      {title ? <title>{title}</title> : null}
      <path d={PATHS[name]} />
    </svg>
  );
}
