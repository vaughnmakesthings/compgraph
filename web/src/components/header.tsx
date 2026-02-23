"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ThemeToggle } from "@/components/theme-toggle";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  return (
    <header role="banner" className="sticky top-0 z-20 flex h-14 items-center gap-4 border-b border-border bg-background px-6 shadow-sm">
      <div className="flex items-baseline gap-3">
        <h1 className="font-display text-[15px] font-semibold tracking-[-0.01em] text-foreground">
          {title}
        </h1>
        {subtitle && (
          <>
            <span aria-hidden="true" className="text-border">
              /
            </span>
            <span className="text-[13px] font-normal text-muted-foreground">
              {subtitle}
            </span>
          </>
        )}
      </div>

      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />

        <Avatar className="size-7" role="img" aria-label="Signed in as VM">
          <AvatarFallback className="bg-primary text-[11px] font-semibold text-primary-foreground">
            VM
          </AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
