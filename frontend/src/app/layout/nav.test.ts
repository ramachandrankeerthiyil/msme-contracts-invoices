import { describe, expect, it } from 'vitest'

import { findActiveNavTarget } from './nav'

const TARGETS = [
  '/',
  '/contracts/dashboard',
  '/contracts',
  '/contracts/upload',
  '/invoices/dashboard',
  '/invoices',
  '/invoices/upload',
]

describe('PLT_001_AC3 findActiveNavTarget', () => {
  it.each([
    ['/', '/'],
    ['/contracts', '/contracts'],
    ['/contracts/', '/contracts'],
    ['/contracts/dashboard', '/contracts/dashboard'],
    ['/contracts/upload', '/contracts/upload'],
    ['/contracts/3f1c-uuid', '/contracts'],
    ['/invoices', '/invoices'],
    ['/invoices/upload', '/invoices/upload'],
    ['/nope', undefined],
    ['/contractsX', undefined],
  ])('%s → %s', (path, expected) => {
    expect(findActiveNavTarget(path, TARGETS)).toBe(expected)
  })
})
