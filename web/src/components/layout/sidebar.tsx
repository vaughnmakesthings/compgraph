"use client";

import { startTransition, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  HomeIcon,
  BuildingOfficeIcon,
  BuildingStorefrontIcon,
  ChartBarIcon,
  BriefcaseIcon,
  BeakerIcon,
  Cog6ToothIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";

interface NavChild {
  id: string;
  label: string;
  href: string;
  color?: string;
  count?: number;
}

interface NavCategory {
  id: string;
  label: string;
  count?: number;
  children: NavChild[];
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  href: string;
  children?: NavChild[];
  categories?: NavCategory[];
}

interface NavSection {
  id: string;
  label: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    id: "intelligence",
    label: "INTELLIGENCE",
    items: [
      {
        id: "dashboard",
        label: "Dashboard",
        icon: HomeIcon,
        href: "/",
      },
      {
        id: "competitors",
        label: "Competitors",
        icon: BuildingOfficeIcon,
        href: "/competitors",
        children: [
          { id: "troc", label: "T-ROC", href: "/competitors/troc" },
          { id: "bds", label: "BDS Connected Solutions", href: "/competitors/bds" },
          { id: "marketsource", label: "MarketSource", href: "/competitors/marketsource" },
          { id: "osl", label: "OSL Retail Services", href: "/competitors/osl" },
          { id: "2020", label: "2020 Companies", href: "/competitors/2020" },
        ],
      },
      {
        id: "prospects",
        label: "Prospects",
        icon: BuildingStorefrontIcon,
        href: "/prospects",
      },
      {
        id: "market",
        label: "Market Overview",
        icon: ChartBarIcon,
        href: "/market",
      },
      {
        id: "hiring",
        label: "Job Feed",
        icon: BriefcaseIcon,
        href: "/hiring",
      },
    ],
  },
  {
    id: "system",
    label: "SYSTEM",
    items: [
      {
        id: "eval",
        label: "Prompt Evaluation Tool",
        icon: BeakerIcon,
        href: "/eval",
        children: [
          { id: "runs", label: "Runs", href: "/eval/runs" },
          { id: "review", label: "Review", href: "/eval/review" },
          { id: "accuracy", label: "Accuracy", href: "/eval/accuracy" },
          { id: "leaderboard", label: "Leaderboard", href: "/eval/leaderboard" },
          { id: "prompt-diff", label: "Run Diff", href: "/eval/prompt-diff" },
        ],
      },
      {
        id: "settings",
        label: "Settings",
        icon: Cog6ToothIcon,
        href: "/settings",
      },
    ],
  },
];

const STORAGE_KEY = "cg-sidebar-state";

function readStoredState(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Record<string, boolean>;
  } catch {
    return {};
  }
}

function writeStoredState(state: Record<string, boolean>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // storage unavailable — continue without persistence
  }
}

function buildDefaultExpanded(): Record<string, boolean> {
  const defaults: Record<string, boolean> = {};
  for (const section of NAV_SECTIONS) {
    for (const item of section.items) {
      const hasSubItems =
        (item.children?.length ?? 0) > 0 || (item.categories?.length ?? 0) > 0;
      if (hasSubItems) {
        defaults[item.id] = true;
        for (const cat of item.categories ?? []) {
          defaults[`${item.id}-${cat.id}`] = true;
        }
      }
    }
  }
  return defaults;
}

interface CountBadgeProps {
  count: number;
}

function CountBadge({ count }: CountBadgeProps) {
  return (
    <span
      className="ml-auto shrink-0 rounded-sm px-1.5 py-0.5 text-[10px] font-semibold leading-none"
      style={{
        backgroundColor: "rgba(255,255,255,0.12)",
        color: "rgba(255,255,255,0.7)",
        fontFamily: "var(--font-mono)",
      }}
    >
      {count}
    </span>
  );
}

interface Tier2ItemProps {
  item: NavChild;
  isActive: boolean;
}

interface Tier2ItemProps {
  item: NavChild;
  isActive: boolean;
  indent?: number;
}

function Tier2Item({ item, isActive, indent = 36 }: Tier2ItemProps) {
  return (
    <Link
      href={item.href}
      className="flex items-center gap-2 rounded-[4px] py-1.5 pr-3 text-sm transition-colors duration-150"
      style={{
        paddingLeft: `${indent}px`,
        color: isActive ? "#EF8354" : "rgba(255,255,255,0.6)",
        backgroundColor: isActive ? "rgba(239,131,84,0.08)" : "transparent",
      }}
      aria-current={isActive ? "page" : undefined}
    >
      <span
        className="shrink-0 rounded-full"
        style={{
          width: "6px",
          height: "6px",
          backgroundColor: item.color ?? "#EF8354",
          boxShadow: isActive ? `0 0 4px ${item.color ?? "#EF8354"}` : "none",
        }}
        aria-hidden="true"
      />
      <span className="flex-1 truncate">{item.label}</span>
      {item.count !== undefined && <CountBadge count={item.count} />}
    </Link>
  );
}

interface Tier1CategoryProps {
  parentId: string;
  category: NavCategory;
  isExpanded: boolean;
  onToggle: (key: string) => void;
  pathname: string;
}

function Tier1Category({
  parentId,
  category,
  isExpanded,
  onToggle,
  pathname,
}: Tier1CategoryProps) {
  const key = `${parentId}-${category.id}`;
  const hasActiveChild = category.children.some((c) => pathname === c.href);

  return (
    <div>
      <button
        type="button"
        onClick={() => onToggle(key)}
        className="flex w-full items-center gap-2 rounded-[4px] py-1 pr-3 text-[11px] font-semibold uppercase tracking-wider transition-colors duration-150"
        style={{
          paddingLeft: "32px",
          color: "rgba(255,255,255,0.4)",
        }}
        aria-expanded={isExpanded}
        aria-controls={`nav-tier2-${category.id}`}
      >
        {hasActiveChild && (
          <span
            className="shrink-0 rounded-full"
            style={{ width: "5px", height: "5px", backgroundColor: "#EF8354" }}
            aria-hidden="true"
          />
        )}
        <span className="flex-1 truncate">{category.label}</span>
        {category.count !== undefined && <CountBadge count={category.count} />}
        <ChevronRightIcon
          className="h-3 w-3 shrink-0 transition-transform duration-150"
          style={{ transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)" }}
          aria-hidden="true"
        />
      </button>

      {isExpanded && category.children.length > 0 && (
        <div id={`nav-tier2-${category.id}`} className="mt-0.5">
          {category.children.map((child) => (
            <Tier2Item
              key={child.id}
              item={child}
              isActive={pathname === child.href}
              indent={48}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface Tier0ItemProps {
  item: NavItem;
  isActive: boolean;
  isExpanded: boolean;
  onToggle: (key: string) => void;
  expandedKeys: Record<string, boolean>;
  pathname: string;
}

function Tier0Item({
  item,
  isActive,
  isExpanded,
  onToggle,
  expandedKeys,
  pathname,
}: Tier0ItemProps) {
  const hasSubItems =
    (item.children?.length ?? 0) > 0 || (item.categories?.length ?? 0) > 0;
  const Icon = item.icon;

  const activeColor = isActive ? "#FFFFFF" : "rgba(255,255,255,0.72)";
  const activeBg = isActive ? "rgba(255,255,255,0.07)" : "transparent";

  if (hasSubItems) {
    return (
      <div>
        <div
          className="relative flex w-full items-center rounded-[4px] transition-colors duration-150 hover:bg-[#3D4357]"
          style={{ color: activeColor, backgroundColor: activeBg }}
        >
          {/* Active indicator bar */}
          <span
            className="absolute left-0 top-1/2 -translate-y-1/2 rounded-r-[3px] transition-opacity duration-150"
            style={{
              width: 3,
              height: 20,
              backgroundColor: "#EF8354",
              opacity: isActive ? 1 : 0,
            }}
            aria-hidden="true"
          />

          {/* Navigable label area */}
          <Link
            href={item.href}
            className="flex flex-1 items-center gap-3 py-2.5 pl-3"
            style={{ color: "inherit" }}
            aria-current={isActive ? "page" : undefined}
          >
            <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
            <span className="flex-1 truncate text-sm font-medium">
              {item.label}
            </span>
          </Link>

          {/* Expand / collapse toggle */}
          <button
            type="button"
            onClick={() => onToggle(item.id)}
            className="flex items-center py-2.5 pr-3 pl-1"
            style={{ color: "inherit" }}
            aria-expanded={isExpanded}
            aria-controls={`nav-sub-${item.id}`}
            aria-label={`${isExpanded ? "Collapse" : "Expand"} ${item.label}`}
          >
            <ChevronRightIcon
              className="h-4 w-4 shrink-0 transition-transform duration-150"
              style={{ transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)" }}
              aria-hidden="true"
            />
          </button>
        </div>

        {isExpanded && (
          <div id={`nav-sub-${item.id}`} className="mt-0.5">
            {/* Flat children */}
            {item.children && item.children.length > 0 && (
              <div className="space-y-0.5 pt-0.5">
                {item.children.map((child) => (
                  <Tier2Item
                    key={child.id}
                    item={child}
                    isActive={pathname === child.href}
                  />
                ))}
                {/* "View all" only for competitor-like lists, not eval sub-pages */}
                {item.id === "competitors" && (
                  <Link
                    href={item.href}
                    className="block transition-colors duration-150 hover:underline"
                    style={{
                      paddingLeft: "36px",
                      paddingTop: "4px",
                      paddingBottom: "6px",
                      fontSize: "11px",
                      fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                      color: "rgba(191,192,192,0.4)",
                    }}
                  >
                    View all →
                  </Link>
                )}
              </div>
            )}

            {/* Grouped children (with collapsible category headers) */}
            {item.categories && item.categories.length > 0 && (
              <div className="space-y-0.5">
                {item.categories.map((cat) => (
                  <Tier1Category
                    key={cat.id}
                    parentId={item.id}
                    category={cat}
                    isExpanded={expandedKeys[`${item.id}-${cat.id}`] ?? true}
                    onToggle={onToggle}
                    pathname={pathname}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // Simple link — no sub-items
  return (
    <Link
      href={item.href}
      className="relative flex items-center gap-3 rounded-[4px] px-3 py-2.5 transition-colors duration-150 hover:bg-[#3D4357] hover:text-white"
      style={{ color: activeColor, backgroundColor: activeBg }}
      aria-current={isActive ? "page" : undefined}
    >
      <span
        className="absolute left-0 top-1/2 -translate-y-1/2 rounded-r-[3px] transition-opacity duration-150"
        style={{
          width: 3,
          height: 20,
          backgroundColor: "#EF8354",
          opacity: isActive ? 1 : 0,
        }}
        aria-hidden="true"
      />
      <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
      <span className="flex-1 truncate text-sm font-medium">{item.label}</span>
    </Link>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        padding: "14px 20px 6px",
        fontSize: "11px",
        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        color: "rgba(191,192,192,0.5)",
      }}
    >
      {children}
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>(
    buildDefaultExpanded
  );

  // Apply persisted state after mount
  useEffect(() => {
    const stored = readStoredState();
    if (Object.keys(stored).length > 0) {
      startTransition(() => setExpandedKeys((prev) => ({ ...prev, ...stored })));
    }
  }, []);

  useEffect(() => {
    writeStoredState(expandedKeys);
  }, [expandedKeys]);

  const handleToggle = useCallback((key: string) => {
    setExpandedKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  return (
    <nav
      className="flex h-full w-[280px] shrink-0 flex-col overflow-y-auto"
      style={{ backgroundColor: "#2D3142" }}
      aria-label="Main navigation"
    >
      {/* Logo block */}
      <div
        style={{
          padding: "20px 20px 18px",
          borderBottom: "1px solid rgba(79,93,117,0.4)",
          marginBottom: "8px",
          flexShrink: 0,
        }}
      >
        <div className="flex items-center gap-2.5">
          <div
            style={{
              width: 32,
              height: 32,
              backgroundColor: "#EF8354",
              borderRadius: "6px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
                fontSize: "14px",
                fontWeight: 700,
                color: "#FFFFFF",
                lineHeight: 1,
              }}
            >
              CG
            </span>
          </div>
          <span
            style={{
              fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
              fontSize: "17px",
              fontWeight: 600,
              color: "#FFFFFF",
            }}
          >
            CompGraph
          </span>
        </div>
      </div>

      {/* Nav sections */}
      <div className="flex-1 px-2 pb-4">
        {NAV_SECTIONS.map((section) => (
          <div key={section.id}>
            <SectionLabel>{section.label}</SectionLabel>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                return (
                  <Tier0Item
                    key={item.id}
                    item={item}
                    isActive={isActive}
                    isExpanded={expandedKeys[item.id] ?? true}
                    onToggle={handleToggle}
                    expandedKeys={expandedKeys}
                    pathname={pathname}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </nav>
  );
}
