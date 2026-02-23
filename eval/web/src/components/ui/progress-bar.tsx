"use client"

import React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const progressBarBackgroundVariants = cva("", {
  variants: {
    variant: {
      default: "bg-blue-200 dark:bg-blue-500/30",
      neutral: "bg-gray-200 dark:bg-gray-500/40",
      warning: "bg-yellow-200 dark:bg-yellow-500/30",
      error: "bg-red-200 dark:bg-red-500/30",
      success: "bg-emerald-200 dark:bg-emerald-500/30",
    },
  },
  defaultVariants: {
    variant: "default",
  },
})

const progressBarFillVariants = cva("", {
  variants: {
    variant: {
      default: "bg-blue-500 dark:bg-blue-500",
      neutral: "bg-gray-500 dark:bg-gray-500",
      warning: "bg-yellow-500 dark:bg-yellow-500",
      error: "bg-red-500 dark:bg-red-500",
      success: "bg-emerald-500 dark:bg-emerald-500",
    },
  },
  defaultVariants: {
    variant: "default",
  },
})

interface ProgressBarProps
  extends React.HTMLProps<HTMLDivElement>,
    VariantProps<typeof progressBarBackgroundVariants> {
  value?: number
  max?: number
  showAnimation?: boolean
  label?: string
}

const ProgressBar = React.forwardRef<HTMLDivElement, ProgressBarProps>(
  (
    {
      value = 0,
      max = 100,
      label,
      showAnimation = false,
      variant,
      className,
      ...props
    },
    forwardedRef,
  ) => {
    const safeValue = Math.min(max, Math.max(value, 0))
    return (
      <div
        ref={forwardedRef}
        className={cn("flex w-full items-center", className)}
        role="progressbar"
        aria-label="Progress bar"
        aria-valuenow={value}
        aria-valuemax={max}
        {...props}
      >
        <div
          className={cn(
            "relative flex h-2 w-full items-center rounded-full",
            progressBarBackgroundVariants({ variant }),
          )}
        >
          <div
            className={cn(
              "h-full flex-col rounded-full",
              progressBarFillVariants({ variant }),
              showAnimation &&
                "transform-gpu transition-all duration-300 ease-in-out",
            )}
            style={{
              width: max ? `${(safeValue / max) * 100}%` : `${safeValue}%`,
            }}
          />
        </div>
        {label ? (
          <span
            className={cn(
              "ml-2 whitespace-nowrap text-sm font-medium leading-none",
              "text-gray-900 dark:text-gray-50",
            )}
          >
            {label}
          </span>
        ) : null}
      </div>
    )
  },
)

ProgressBar.displayName = "ProgressBar"

export { ProgressBar, type ProgressBarProps }
