import { cacheMapSet } from "../../cacheMap";
import type { LayerSession } from "./types";

export const MAX_CACHED_LAYER_SESSIONS = 32;
export const MAX_CACHED_FILE_DESIGNS = 32;

export function cacheLayerSession(cache: Map<string, LayerSession>, key: string, session: LayerSession) {
  cacheMapSet(cache, key, session, MAX_CACHED_LAYER_SESSIONS);
}

export function clampLayerListHeight(value: number) {
  const maxHeight = Math.max(60, window.innerHeight - 310);
  const minHeight = Math.min(150, maxHeight);
  return Math.max(minHeight, Math.min(maxHeight, value));
}
