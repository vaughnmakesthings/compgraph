"use client"

import React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const progressCircleBackgroundVariants = cva("", {
  variants: {
    variant: {
      default: "stroke-blue-200 dark:stroke-blue-500/30",
      neutral: "stroke-gray-200 dark:stroke-gray-500/40",
      warning: "stroke-yellow-200 dark:stroke-yellow-500/30",
      error: "stroke-red-200 dark:stroke-red-500/30",
      success: "stroke-emerald-200 dark:stroke-emerald-500/30",
    },
  },
  defaultVariants: {
    variant: "default",
  },
})

const progressCircleFillVariants = cva("", {
  variants: {
    variant: {
      default: "stroke-blue-500 dark:stroke-blue-500",
      neutral: "stroke-gray-500 dark:stroke-gray-500",
      warning: "stroke-yellow-500 dark:stroke-yellow-500",
      error: "stroke-red-500 dark:stroke-red-500",
      success: "stroke-emerald-500 dark:stroke-emerald-500",
    },
  },
  defaultVariants: {
    variant: "default",
  },
})

interface ProgressCircleProps
  extends Omit<React.SVGProps<SVGSVGElement>, "value">,
    VariantProps<typeof progressCircleBackgroundVariants> {
  value?: number
  max?: number
  showAnimation?: boolean
  radius?: number
  strokeWidth?: number
  children?: React.ReactNode
}

const ProgressCircle = React.forwardRef<SVGSVGElement, ProgressCircleProps>(
  (
    {
      value = 0,
      max = 100,
      radius = 32,
      strokeWidth = 6,
      showAnimation = true,
      variant,
      className,
      children,
      ...props
    },
    forwardedRef,
  ) => {
    const safeValue = Math.min(max, Math.max(value, 0))
    const normalizedRadius = radius - strokeWidth / 2
    const circumference = normalizedRadius * 2 * Math.PI
    const offset = circumference - (safeValue / max) * circumference

    return (
      <div
        className={cn("relative")}
        role="progressbar"
        aria-label="Progress circle"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        data-max={max}
        data-value={safeValue ?? null}
      >
        <svg
          ref={forwardedRef}
          width={radius * 2}
          height={radius * 2}
          viewBox={`0 0 ${radius * 2} ${radius * 2}`}
          className={cn("-rotate-90 transform", className)}
          {...props}
        >
          <circle
            r={normalizedRadius}
            cx={radius}
            cy={radius}
            strokeWidth={strokeWidth}
            fill="transparent"
            stroke=""
            strokeLinecap="round"
            className={cn(
              "transition-colors ease-linear",
              progressCircleBackgroundVariants({ variant }),
            )}
          />
          {safeValue >= 0 ? (
            <circle
              r={normalizedRadius}
              cx={radius}
              cy={radius}
              strokeWidth={strokeWidth}
              strokeDasharray={`${circumference} ${circumference}`}
              strokeDashoffset={offset}
              fill="transparent"
              stroke=""
              strokeLinecap="round"
              className={cn(
                "transition-colors ease-linear",
                progressCircleFillVariants({ variant }),
                showAnimation &&
                  "transform-gpu transition-all duration-300 ease-in-out",
              )}
            />
          ) : null}
        </svg>
        <div
          className={cn("absolute inset-0 flex items-center justify-center")}
        >
          {children}
        </div>
      </div>
    )
  },
)

ProgressCircle.displayName = "ProgressCircle"

export { ProgressCircle, type ProgressCircleProps }
