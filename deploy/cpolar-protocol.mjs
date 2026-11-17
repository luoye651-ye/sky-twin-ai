// Actual cpolar 3.3.12 logfmt tunnel event. Ignore auth logs and unrelated URLs.
export function establishedHttpsOrigin(line) {
  if (!line.includes('Tunnel established at https://')) return ''
  const value = line.match(/https:\/\/[a-z0-9.-]+(?::\d+)?/i)?.[0] || ''
  try {
    const url = new URL(value)
    if (url.protocol !== 'https:' || url.origin !== value || !/\.(?:cpolar\.(?:cn|top|io|com|vip|net))$/.test(url.hostname)) return ''
    if (['www.cpolar.com', 'dashboard.cpolar.com', 'api.cpolar.com'].includes(url.hostname)) return ''
    return value
  } catch { return '' }
}
