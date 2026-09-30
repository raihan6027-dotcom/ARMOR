"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";

import s from "./camera.module.css";

export type CameraState = "starting" | "ready" | "denied" | "unavailable";

export interface CameraHandle {
  /** JPEG data URL of the current frame (not mirrored), or null if not ready. */
  capture(): string | null;
}

export const Camera = forwardRef<CameraHandle, { onState?: (s: CameraState) => void; ok?: boolean }>(
  function Camera({ onState, ok }, ref) {
    const video = useRef<HTMLVideoElement>(null);
    const [state, setState] = useState<CameraState>("starting");

    useEffect(() => {
      let stream: MediaStream | null = null;
      let cancelled = false;
      const update = (st: CameraState) => {
        if (cancelled) return;
        setState(st);
        onState?.(st);
      };
      (async () => {
        if (!navigator.mediaDevices?.getUserMedia) return update("unavailable");
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 1280 } },
            audio: false,
          });
          if (cancelled) return stream.getTracks().forEach((t) => t.stop());
          if (video.current) {
            video.current.srcObject = stream;
            await video.current.play().catch(() => undefined);
          }
          update("ready");
        } catch (err) {
          const name = (err as DOMException)?.name;
          update(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "unavailable");
        }
      })();
      return () => {
        cancelled = true;
        stream?.getTracks().forEach((t) => t.stop());
      };
    }, [onState]);

    useImperativeHandle(ref, () => ({
      capture() {
        const v = video.current;
        if (!v || state !== "ready" || !v.videoWidth) return null;
        const canvas = document.createElement("canvas");
        canvas.width = v.videoWidth;
        canvas.height = v.videoHeight;
        canvas.getContext("2d")?.drawImage(v, 0, 0);
        return canvas.toDataURL("image/jpeg", 0.9);
      },
    }));

    return (
      <div className={s.frame} data-ok={ok ? "true" : undefined}>
        <video ref={video} className={s.video} playsInline muted aria-label="Pratinjau kamera" />
        <span aria-hidden="true" className={`${s.corner} ${s.tl}`} />
        <span aria-hidden="true" className={`${s.corner} ${s.tr}`} />
        <span aria-hidden="true" className={`${s.corner} ${s.bl}`} />
        <span aria-hidden="true" className={`${s.corner} ${s.br}`} />
        <span aria-hidden="true" className={s.oval} />
        {state === "starting" ? <p className={s.status}>Menyalakan kamera...</p> : null}
      </div>
    );
  },
);

/** Read files picked from the device as data URLs. */
export function readFiles(files: FileList | null): Promise<string[]> {
  return Promise.all(
    Array.from(files ?? []).map(
      (f) =>
        new Promise<string>((resolve, reject) => {
          const r = new FileReader();
          r.onload = () => resolve(String(r.result));
          r.onerror = () => reject(r.error);
          r.readAsDataURL(f);
        }),
    ),
  );
}
