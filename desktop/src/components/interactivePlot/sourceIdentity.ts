import type { SourceInfo } from "../../../ipc/protocol";

const COMBINED_IDENTITY = "\u0000combined";

/** Identity of a source that survives index shifts when files are added or removed. */
export function sourceIdentity(source: Pick<SourceInfo, "path" | "name" | "is_combined">): string {
  if (source.is_combined) return COMBINED_IDENTITY;
  return String(source.path ?? source.name);
}

/**
 * Re-key index-keyed per-file state after the source list changed.
 *
 * The derived Combined source always sits after the real files, so loading a
 * file moves it to a new index and the new file takes its old one. Entries
 * whose source is gone are dropped instead of attaching to whatever file now
 * owns that index.
 */
export function remapByIdentity<T>(
  byIndex: Record<number, T>,
  previous: readonly string[],
  next: readonly string[],
): Record<number, T> {
  const nextIndexByIdentity = new Map<string, number>();
  next.forEach((identity, index) => {
    if (!nextIndexByIdentity.has(identity)) nextIndexByIdentity.set(identity, index);
  });
  const result: Record<number, T> = {};
  for (const [key, value] of Object.entries(byIndex)) {
    const identity = previous[Number(key)];
    if (identity === undefined) continue;
    const index = nextIndexByIdentity.get(identity);
    if (index !== undefined) result[index] = value;
  }
  return result;
}
