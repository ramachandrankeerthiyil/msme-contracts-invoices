/**
 * Picks the sidebar item to highlight: the longest nav target that is the current path or a
 * parent of it, so `/contracts/123` highlights "All contracts" (`/contracts`) and
 * `/contracts/upload` highlights "Upload contract" rather than "All contracts" (PLT-001 AC3).
 */
export function findActiveNavTarget(pathname: string, targets: readonly string[]): string | undefined {
  const path = pathname.replace(/\/+$/, '') || '/'
  let best: string | undefined
  for (const target of targets) {
    const matches = target === '/' ? path === '/' : path === target || path.startsWith(`${target}/`)
    if (matches && (best === undefined || target.length > best.length)) best = target
  }
  return best
}
