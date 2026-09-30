"use client";

import { createContext, useCallback, useContext, useState } from "react";

import { Icon } from "./Icon";
import s from "./ui.module.css";

interface ToastItem {
  id: number;
  text: string;
}

const ToastContext = createContext<(text: string) => void>(() => undefined);

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const show = useCallback((text: string) => {
    const id = Date.now() + Math.random();
    setItems((cur) => [...cur, { id, text }]);
    window.setTimeout(() => setItems((cur) => cur.filter((t) => t.id !== id)), 3200);
  }, []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className={s.toastWrap} aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={s.toast}>
            <Icon name="check" size={18} />
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
