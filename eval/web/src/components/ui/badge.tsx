"use client"

import React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-x-1 whitespace-nowrap rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset",
  {
    variants: {
      variant: {
        default: [
          "bg-accent text-accent-foreground ring-primary/20",
          "dark:bg-accent dark:text-accent-foreground dark:ring-primary/30",
        ],
        neutral: [
          "bg-muted text-muted-foreground ring-border/30",
          "dark:bg-muted dark:text-muted-foreground dark:ring-border/20",
        ],
        success: [
          "bg-success-muted text-success ring-success/30",
          "dark:bg-success-muted dark:text-success dark:ring-success/20",
        ],
        error: [
          "bg-error-muted text-error ring-error/20",
          "dark:bg-error-muted dark:text-error dark:ring-error/20",
        ],
        warning: [
          "bg-warning-muted text-warning-foreground ring-warning/30",
          "dark:bg-warning-muted dark:text-warning dark:ring-warning/20",
        ],
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
)

interface BadgeProps
  extends React.ComponentPropsWithoutRef<"span">,
    VariantProps<typeof badgeVariants> {}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, ...props }, forwardedRef) => {
    return (
      <span
        ref={forwardedRef}
        className={cn(badgeVariants({ variant }), className)}
        {...props}
      />
    )
  },
)

Badge.displayName = "Badge"

export { Badge, badgeVariants, type BadgeProps }
