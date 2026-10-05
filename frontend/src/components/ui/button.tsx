import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { Link, type LinkProps } from 'react-router'

import { cn } from '@/lib/utils'

export type ButtonVariant = 'primary' | 'secondary' | 'danger'

const BASE =
  'inline-flex shrink-0 items-center justify-center gap-2 rounded-md px-5 text-body font-semibold ' +
  'transition-colors disabled:cursor-not-allowed disabled:opacity-60 [&_svg]:size-5 [&_svg]:shrink-0'

// Buttons are 48px tall. `multiline` lets a long label wrap (e.g. in a narrow table column)
// while keeping that minimum height.
const SINGLE_LINE = 'h-12 whitespace-nowrap'
const MULTI_LINE = 'min-h-12 py-2 text-center leading-snug'

const VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-on-primary hover:bg-primary-hover',
  secondary: 'border border-primary bg-bg text-primary hover:bg-surface-strong',
  danger: 'bg-danger text-on-primary hover:opacity-90',
}

export function buttonClasses(
  variant: ButtonVariant = 'primary',
  className?: string,
  multiline = false,
): string {
  return cn(BASE, multiline ? MULTI_LINE : SINGLE_LINE, VARIANTS[variant], className)
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  multiline?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', multiline, className, type = 'button', ...props },
  ref,
) {
  return <button ref={ref} type={type} className={buttonClasses(variant, className, multiline)} {...props} />
})

export interface ButtonLinkProps extends LinkProps {
  variant?: ButtonVariant
}

/** A router link that looks like a button (e.g. the page's primary action). */
export function ButtonLink({ variant = 'primary', className, ...props }: ButtonLinkProps) {
  return <Link className={buttonClasses(variant, className)} {...props} />
}
