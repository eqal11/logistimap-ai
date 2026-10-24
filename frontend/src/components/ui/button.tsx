import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../services/utils'
// Source-owned shadcn/ui-style Radix primitive adapted to the product theme.
const variants = cva('button inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:pointer-events-none disabled:opacity-40', {
  variants: {
    variant: { default: 'button-primary', outline: 'button-outline', ghost: 'button-ghost' },
    size: { default: 'h-9 px-3.5 text-xs', icon: 'h-9 w-9 p-0', sm: 'h-7 px-2.5 text-xs' },
  }, defaultVariants: { variant: 'default', size: 'default' },
})
export function Button({ className, variant, size, asChild = false, type = 'button', ...props }:
React.ComponentProps<'button'> & VariantProps<typeof variants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : 'button'
  return <Component type={type} className={cn(variants({ variant, size, className }))} {...props} />
}
