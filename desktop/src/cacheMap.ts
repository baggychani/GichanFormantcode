/** Bounded Map: insert refreshes recency; oldest entries are evicted past `limit`. */

export function cacheMapSet<K, V>(cache: Map<K, V>, key: K, value: V, limit: number) {
  if (key === undefined || key === null) return;
  cache.delete(key);
  cache.set(key, value);
  while (cache.size > Math.max(1, limit)) {
    const oldest = cache.keys().next().value as K | undefined;
    if (oldest === undefined) break;
    cache.delete(oldest);
  }
}
