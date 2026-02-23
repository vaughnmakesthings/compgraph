"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  FlaskConical,
  GitCompareArrows,
  Trophy,
  ClipboardCheck,
  FileDiff,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SIDEBAR_WIDTH, SIDEBAR_WIDTH_COLLAPSED } from "@/lib/constants";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface NavItemDef {
  label: string;
  href: string;
  icon: LucideIcon;
}

interface NavGroup {
  label: string;
  items: NavItemDef[];
}

const navGroups: NavGroup[] = [
  {
    label: "Analysis",
    items: [
      { label: "Leaderboard", href: "/leaderboard", icon: Trophy },
      { label: "Accuracy Review", href: "/accuracy", icon: ClipboardCheck },
      { label: "A/B Compare", href: "/review", icon: GitCompareArrows },
      { label: "Run Diff", href: "/prompt-diff", icon: FileDiff },
    ],
  },
  {
    label: "Management",
    items: [
      { label: "Run Tests", href: "/runs", icon: FlaskConical },
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
    ],
  },
];

const bottomItems: NavItemDef[] = [
  { label: "Settings", href: "/settings", icon: Settings },
];

function NavItem({
  item,
  isActive,
  collapsed,
}: {
  item: NavItemDef;
  isActive: boolean;
  collapsed: boolean;
}) {
  const content = (
    <Link
      href={item.href}
      className={cn(
        "group relative flex items-center gap-3 overflow-visible rounded-md px-3 py-2 text-[13px] transition-colors duration-150",
        isActive
          ? "bg-sidebar-accent font-semibold text-sidebar-primary"
          : "font-medium text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        collapsed && "justify-center px-2"
      )}
    >
      {isActive && (
        <span
          aria-hidden="true"
          className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-sidebar-primary"
        />
      )}
      <item.icon
        className={cn(
          "size-[18px] shrink-0 transition-colors duration-150",
          isActive
            ? "text-sidebar-primary"
            : "text-sidebar-foreground group-hover:text-sidebar-accent-foreground"
        )}
        strokeWidth={isActive ? 2 : 1.5}
      />
      <span
        className={cn(
          "overflow-hidden whitespace-nowrap transition-[max-width,opacity] duration-200 ease-in-out",
          collapsed ? "max-w-0 opacity-0" : "max-w-[160px] opacity-100"
        )}
      >
        {item.label}
      </span>
    </Link>
  );

  if (collapsed) {
    return (
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent
          side="right"
          sideOffset={12}
          className="text-xs font-medium"
        >
          {item.label}
        </TooltipContent>
      </Tooltip>
    );
  }

  return content;
}

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className="fixed inset-y-0 left-0 z-30 flex flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-200 ease-in-out will-change-[width]"
      style={{ width: collapsed ? SIDEBAR_WIDTH_COLLAPSED : SIDEBAR_WIDTH }}
    >
      {/* Logo */}
      <div
        className={cn(
          "flex h-14 shrink-0 items-center border-b border-sidebar-border",
          collapsed ? "justify-center px-2" : "px-5"
        )}
      >
        <div className="flex items-center gap-2.5">
          <div className="flex h-6 w-8 shrink-0 items-center justify-center rounded-md bg-sidebar-primary">
            <span className="text-[11px] font-bold tracking-[-0.03em] text-sidebar-primary-foreground">
              CG
            </span>
          </div>
          <span
            className={cn(
              "font-display overflow-hidden whitespace-nowrap text-[15px] font-semibold tracking-[-0.01em] text-sidebar-accent-foreground transition-[max-width,opacity] duration-200 ease-in-out",
              collapsed ? "max-w-0 opacity-0" : "max-w-[160px] opacity-100"
            )}
          >
            CompGraph
          </span>
        </div>
      </div>

      {/* Main nav */}
      <nav aria-label="Main navigation" className="flex-1 overflow-y-auto px-3 pt-3">
        {navGroups.map((group) => (
          <div key={group.label} className="mb-3">
            {!collapsed && (
              <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">
                {group.label}
              </p>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                return (
                  <NavItem
                    key={item.href}
                    item={item}
                    isActive={isActive}
                    collapsed={collapsed}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="space-y-0.5 border-t border-sidebar-border px-3 py-3">
        {bottomItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <NavItem
              key={item.href}
              item={item}
              isActive={isActive}
              collapsed={collapsed}
            />
          );
        })}

        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <button
              onClick={onToggle}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              className="flex w-full items-center justify-center rounded-md p-2 text-sidebar-foreground/70 transition-colors duration-150 hover:bg-sidebar-accent hover:text-sidebar-foreground"
            >
              {collapsed ? (
                <PanelLeftOpen className="size-4" />
              ) : (
                <PanelLeftClose className="size-4" />
              )}
            </button>
          </TooltipTrigger>
          <TooltipContent
            side={collapsed ? "right" : "top"}
            sideOffset={8}
            className="text-xs"
          >
            {collapsed ? "Expand sidebar" : "Collapse sidebar"}
          </TooltipContent>
        </Tooltip>
      </div>
    </aside>
  );
}
