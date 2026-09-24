import { clsx, type ClassValue } from 'clsx'

// Plain clsx on purpose: tailwind-merge would treat our token utilities `text-h1` (size) and
// `text-text` (colour) as conflicting and drop one of them.
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs)
}
