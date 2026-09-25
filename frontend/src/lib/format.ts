// Display formatting (ui-design-system.md "Formatting"): dates as `24 Sep 2026`, money as INR
// with Indian digit grouping, relative due hints. Business "today" is Asia/Kolkata.

export const APP_TIME_ZONE = 'Asia/Kolkata'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/

/** Today's date in the business time zone, as `YYYY-MM-DD`. */
export function todayIso(now: Date = new Date()): string {
  // en-CA formats as YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: APP_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now)
}

/**
 * `2026-09-24` → `24 Sep 2026`. Accepts a date (`YYYY-MM-DD`) or a timestamp; timestamps are
 * converted to the business time zone first. (Intl's en-IN short month for September is
 * "Sept", which the design system rules out, hence the fixed month names.)
 */
export function formatDate(value: string): string {
  const iso = ISO_DATE.test(value) ? value : todayIso(new Date(value))
  const [, year, month, day] = ISO_DATE.exec(iso) ?? []
  if (!year || !month || !day) return value
  return `${Number(day)} ${MONTHS[Number(month) - 1]} ${year}`
}

const TIME_FORMAT = new Intl.DateTimeFormat('en-IN', {
  timeZone: APP_TIME_ZONE,
  hour: 'numeric',
  minute: '2-digit',
  hour12: true,
})

/** `2026-09-24T05:12:44Z` → `24 Sep 2026, 10:42 am` (business time zone). */
export function formatDateTime(timestamp: string): string {
  const moment = new Date(timestamp)
  if (Number.isNaN(moment.getTime())) return timestamp
  // Some ICU versions put a narrow no-break space before "am"; normalise it.
  const time = TIME_FORMAT.format(moment).replace(/\s+/g, ' ').toLowerCase()
  return `${formatDate(timestamp)}, ${time}`
}

/** `2350000` → `2.2 MB`. */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Groups an integer string the Indian way: 425000 → 4,25,000; 12345678 → 1,23,45,678. */
function groupIndian(digits: string): string {
  if (digits.length <= 3) return digits
  const lastThree = digits.slice(-3)
  const rest = digits.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ',')
  return `${rest},${lastThree}`
}

/**
 * `"425000.00"` → `₹4,25,000.00`. Works on the decimal string from the API, so there is no
 * floating-point rounding.
 */
export function formatINR(amount: string | number): string {
  const text = typeof amount === 'number' ? amount.toFixed(2) : amount.trim()
  const match = /^(-)?(\d+)(?:\.(\d+))?$/.exec(text)
  if (!match) return text
  const [, sign = '', whole = '0', fraction = ''] = match
  const paise = fraction.padEnd(2, '0').slice(0, 2)
  const rupees = groupIndian(whole.replace(/^0+(?=\d)/, ''))
  return `${sign}₹${rupees}.${paise}`
}

function daysBetween(fromIso: string, toIso: string): number {
  const toUtc = (iso: string) => {
    const [, y, m, d] = ISO_DATE.exec(iso) ?? []
    return Date.UTC(Number(y), Number(m) - 1, Number(d))
  }
  return Math.round((toUtc(toIso) - toUtc(fromIso)) / 86_400_000)
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`
}

/** `3` → `due in 3 days`, `0` → `due today`, `-12` → `12 days overdue`. */
export function dueHintFromDays(days: number): string {
  if (days === 0) return 'due today'
  if (days > 0) return `due in ${plural(days, 'day')}`
  return `${plural(-days, 'day')} overdue`
}

/** `due today`, `due in 3 days`, `12 days overdue`. */
export function relativeDue(dueDate: string, today: string = todayIso()): string {
  return dueHintFromDays(daysBetween(today, dueDate))
}

/** `2026-09-24` → `24 Sep` (dates or timestamps). */
export function formatDayMonth(value: string): string {
  return formatDate(value).replace(/ \d{4}$/, '')
}

/** `24 Sep – 30 Sep 2026`; the start keeps its year only when the years differ. */
export function formatDateRange(from: string, to: string): string {
  const sameYear = from.slice(0, 4) === to.slice(0, 4)
  return `${sameYear ? formatDayMonth(from) : formatDate(from)} – ${formatDate(to)}`
}

/** `1 invoice`, `18 invoices` (Indian digit grouping). */
export function countOf(n: number, singular: string, plural = `${singular}s`): string {
  return `${n.toLocaleString('en-IN')} ${n === 1 ? singular : plural}`
}
