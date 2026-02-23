"use client"

import React from "react"

import {
  AvailableChartColors,
  type AvailableChartColorsKeys,
  getColorClassName,
} from "@/lib/chart-utils"
import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

const getMarkerBgColor = (
  marker: number | undefined,
  values: number[],
  colors: AvailableChartColorsKeys[],
): string => {
  if (marker === undefined) return ""

  if (marker === 0) {
    for (let index = 0; index < values.length; index++) {
      if (values[index] > 0) {
        return getColorClassName(colors[index], "bg")
      }
    }
  }

  let prefixSum = 0
  for (let index = 0; index < values.length; index++) {
    prefixSum += values[index]
    if (prefixSum >= marker) {
      return getColorClassName(colors[index], "bg")
    }
  }

  return getColorClassName(colors[values.length - 1], "bg")
}

const getPositionLeft = (
  value: number | undefined,
  maxValue: number,
): number => (value ? (value / maxValue) * 100 : 0)

const sumNumericArray = (arr: number[]) =>
  arr.reduce((prefixSum, num) => prefixSum + num, 0)

const formatNumber = (num: number): string => {
  if (Number.isInteger(num)) {
    return num.toString()
  }
  return num.toFixed(1)
}

const BarLabels = ({ values }: { values: number[] }) => {
  const sumValues = React.useMemo(() => sumNumericArray(values), [values])

  const labelData = React.useMemo(() => {
    const result: {
      prefixSum: number
      showLabel: boolean
      widthPositionLeft: number
    }[] = []
    let runningSum = 0
    let consecutiveHidden = 0

    for (let i = 0; i < values.length; i++) {
      runningSum += values[i]

      const showLabel =
        (values[i] >= 0.1 * sumValues ||
          consecutiveHidden >= 0.09 * sumValues) &&
        sumValues - runningSum >= 0.1 * sumValues &&
        runningSum >= 0.1 * sumValues &&
        runningSum < 0.9 * sumValues

      consecutiveHidden = showLabel ? 0 : consecutiveHidden + values[i]

      result.push({
        prefixSum: runningSum,
        showLabel,
        widthPositionLeft: getPositionLeft(values[i], sumValues),
      })
    }
    return result
  }, [values, sumValues])

  return (
    <div
      className={cn(
        "relative mb-2 flex h-5 w-full text-sm font-medium",
        "text-gray-700 dark:text-gray-300",
      )}
    >
      <div className="absolute bottom-0 left-0 flex items-center">0</div>
      {values.map((_, index) => {
        const { prefixSum, showLabel, widthPositionLeft } = labelData[index]

        return (
          <div
            key={`item-${index}`}
            className="flex items-center justify-end pr-0.5"
            style={{ width: `${widthPositionLeft}%` }}
          >
            {showLabel ? (
              <span
                className={cn("block translate-x-1/2 text-sm tabular-nums")}
              >
                {formatNumber(prefixSum)}
              </span>
            ) : null}
          </div>
        )
      })}
      <div className="absolute bottom-0 right-0 flex items-center">
        {formatNumber(sumValues)}
      </div>
    </div>
  )
}

interface CategoryBarProps extends React.HTMLAttributes<HTMLDivElement> {
  values: number[]
  colors?: AvailableChartColorsKeys[]
  marker?: { value: number; tooltip?: string; showAnimation?: boolean }
  showLabels?: boolean
}

const CategoryBar = React.forwardRef<HTMLDivElement, CategoryBarProps>(
  (
    {
      values = [],
      colors = AvailableChartColors,
      marker,
      showLabels = true,
      className,
      ...props
    },
    forwardedRef,
  ) => {
    const markerBgColor = React.useMemo(
      () => getMarkerBgColor(marker?.value, values, colors),
      [marker, values, colors],
    )

    const maxValue = React.useMemo(() => sumNumericArray(values), [values])

    const adjustedMarkerValue = React.useMemo(() => {
      if (marker === undefined) return undefined
      if (marker.value < 0) return 0
      if (marker.value > maxValue) return maxValue
      return marker.value
    }, [marker, maxValue])

    const markerPositionLeft: number = React.useMemo(
      () => getPositionLeft(adjustedMarkerValue, maxValue),
      [adjustedMarkerValue, maxValue],
    )

    return (
      <div
        ref={forwardedRef}
        className={cn(className)}
        role="meter"
        aria-label="Category bar"
        aria-valuenow={marker?.value ?? 0}
        aria-valuemin={0}
        aria-valuemax={sumNumericArray(values)}
        {...props}
      >
        {showLabels ? <BarLabels values={values} /> : null}
        <div className="relative flex h-2 w-full items-center">
          <div className="flex h-full flex-1 items-center gap-0.5 overflow-hidden rounded-full">
            {values.map((value, index) => {
              const barColor = colors[index] ?? "slate"
              const percentage = (value / maxValue) * 100
              return (
                <div
                  key={`item-${index}`}
                  className={cn(
                    "h-full",
                    getColorClassName(
                      barColor as AvailableChartColorsKeys,
                      "bg",
                    ),
                    percentage === 0 && "hidden",
                  )}
                  style={{ width: `${percentage}%` }}
                />
              )
            })}
          </div>

          {marker !== undefined ? (
            <div
              className={cn(
                "absolute w-2 -translate-x-1/2",
                marker.showAnimation &&
                  "transform-gpu transition-all duration-300 ease-in-out",
              )}
              style={{
                left: `${markerPositionLeft}%`,
              }}
            >
              {marker.tooltip ? (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        aria-hidden="true"
                        className={cn(
                          "relative mx-auto h-4 w-1 rounded-full ring-2",
                          "ring-white dark:ring-gray-950",
                          markerBgColor,
                        )}
                      >
                        <div
                          aria-hidden
                          className="absolute size-7 -translate-x-[45%] -translate-y-[15%]"
                        />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>{marker.tooltip}</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              ) : (
                <div
                  className={cn(
                    "mx-auto h-4 w-1 rounded-full ring-2",
                    "ring-white dark:ring-gray-950",
                    markerBgColor,
                  )}
                />
              )}
            </div>
          ) : null}
        </div>
      </div>
    )
  },
)

CategoryBar.displayName = "CategoryBar"

export { CategoryBar, type CategoryBarProps }
