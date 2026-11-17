export function tokenCookieName() {
  return typeof document !== 'undefined' && document.querySelector?.('meta[name="skytwin-demo"]')?.getAttribute('content') === 'isolated' ? 'SkyTwin-Demo-Token' : 'Admin-Token'
}
export const isolatedDemo = tokenCookieName() === 'SkyTwin-Demo-Token'
