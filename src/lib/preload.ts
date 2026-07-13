import { createContext, useContext } from "react";
import type { PageMeta } from "./data";

export interface Preload {
  route: string;
  page?: { vendor: string; slug: string; md: string; title: string; num: string; cat: string; source?: string };
  prev?: PageMeta | null;
  next?: PageMeta | null;
  catPages?: PageMeta[];
}

export const PreloadContext = createContext<Preload | null>(null);
export function usePreload() { return useContext(PreloadContext); }

declare global { interface Window { __PRELOAD__?: Preload } }
