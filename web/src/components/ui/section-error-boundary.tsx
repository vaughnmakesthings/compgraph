"use client";

import React, { Component } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { cardStyle, fontBody } from "@/lib/styles";

interface SectionErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  name?: string;
}

interface SectionErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class SectionErrorBoundary extends Component<
  SectionErrorBoundaryProps,
  SectionErrorBoundaryState
> {
  constructor(props: SectionErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): SectionErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error(
      `[SectionErrorBoundary${this.props.name ? `: ${this.props.name}` : ""}]`,
      error,
      errorInfo.componentStack
    );
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): React.ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    return (
      <div
        className="rounded-lg border p-4 mb-6"
        style={cardStyle}
        role="alert"
      >
        <div className="flex items-center justify-between">
          <div style={fontBody}>
            <p className="text-sm font-medium text-[#2D3142]">
              {this.props.name
                ? `Failed to load ${this.props.name}`
                : "This section encountered an error"}
            </p>
            <p className="mt-1 text-xs text-[#4F5D75]">
              {this.state.error?.message || "An unexpected error occurred"}
            </p>
          </div>
          <button
            type="button"
            onClick={this.handleRetry}
            className="shrink-0 flex items-center gap-1.5 rounded-md border border-[#BFC0C0] bg-white px-3 py-1.5 text-xs font-medium text-[#2D3142] transition-colors hover:bg-[#F4F4F0]"
            style={fontBody}
          >
            <ArrowPathIcon className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      </div>
    );
  }
}
