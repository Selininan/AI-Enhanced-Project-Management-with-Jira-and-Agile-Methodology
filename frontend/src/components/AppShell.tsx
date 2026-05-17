// frontend/src/components/AppShell.tsx
import { Link, useRouterState, Outlet } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Home,
  BarChart3,
  Users,
  FileText,
  MessageSquare,
  Settings,
  RefreshCw,
  GitCompare,
  ChevronDown,
  Building2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { checkHealth, getBaseUrl, setBaseUrl } from "@/lib/api";
import { useProject } from "@/context/ProjectContext";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const nav = [
  { to: "/",                label: "Dashboard",      icon: Home },
  { to: "/sprint-analysis", label: "Sprint Analysis", icon: BarChart3 },
  { to: "/capacity",        label: "Capacity Report", icon: Users },
  { to: "/brd",             label: "BRD Alignment",   icon: FileText },
  { to: "/chat",            label: "AI Support Chat", icon: MessageSquare },
  { to: "/compare",         label: "Compare Projects", icon: GitCompare },
] as const;

export function AppShell() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [connected, setConnected] = useState<boolean | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const { selectedProject, setSelectedProject, projects, projectName } = useProject();

  useEffect(() => {
    let alive = true;
    checkHealth().then((ok) => alive && setConnected(ok));
    return () => { alive = false; };
  }, [refreshKey]);

  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      {/* ── Sidebar ── */}
      <aside className="hidden md:flex w-60 flex-col border-r border-border bg-sidebar">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-md bg-primary text-primary-foreground grid place-items-center font-semibold text-sm">
              B
            </div>
            <div>
              <div className="text-sm font-semibold leading-tight">BAI</div>
              <div className="text-[11px] text-muted-foreground leading-tight">
                Beko AI Sprint
              </div>
            </div>
          </div>
        </div>

        {/* ── Proje Seçici ── */}
        <div className="px-3 py-3 border-b border-border">
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1.5 px-1">
            Active Project
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="w-full flex items-center justify-between gap-2 rounded-md px-3 py-2 text-sm font-medium bg-accent/50 hover:bg-accent transition-colors text-left">
                <div className="flex items-center gap-2 min-w-0">
                  <Building2 className="h-3.5 w-3.5 text-primary shrink-0" />
                  <span className="truncate">{selectedProject}</span>
                </div>
                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-52" align="start">
              <DropdownMenuLabel className="text-xs text-muted-foreground">
                Jira Projects
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              {projects.map((p) => (
                <DropdownMenuItem
                  key={p.key}
                  onClick={() => setSelectedProject(p.key)}
                  className={cn(
                    "flex flex-col items-start gap-0.5 cursor-pointer",
                    selectedProject === p.key && "bg-primary/10 text-primary"
                  )}
                >
                  <span className="font-medium text-xs">{p.key}</span>
                  <span className="text-[11px] text-muted-foreground truncate w-full">
                    {p.name}
                  </span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          {/* Seçili projenin adı */}
          <div className="mt-1.5 px-1 text-[10px] text-muted-foreground truncate">
            {projectName}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((item) => {
            const active =
              item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 text-[11px] text-muted-foreground border-t border-border">
          Capstone · Beko × İstinye
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 md:px-6">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-sm md:text-base font-semibold truncate">
              BAI — {projectName}
            </h1>
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-muted-foreground">
              <span
                className={cn(
                  "h-2 w-2 rounded-full",
                  connected === null
                    ? "bg-muted-foreground/40"
                    : connected
                      ? "bg-[color:var(--success)]"
                      : "bg-[color:var(--danger)]"
                )}
              />
              {connected === null
                ? "Checking…"
                : connected
                  ? "API connected"
                  : "Using mock data"}
            </div>
            {/* Aktif proje badge */}
            <span className="hidden sm:inline-flex items-center rounded-full border border-primary/30 bg-primary/5 px-2 py-0.5 text-[10px] font-semibold text-primary">
              {selectedProject}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setRefreshKey((k) => k + 1);
                window.dispatchEvent(new CustomEvent("bai:refresh"));
              }}
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Refresh Data
            </Button>
            <SettingsDialog onSaved={() => setRefreshKey((k) => k + 1)} />
          </div>
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function SettingsDialog({ onSaved }: { onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [url, setUrl]   = useState(getBaseUrl());
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="ghost">
          <Settings className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>API Settings</DialogTitle>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="api-url">Base URL</Label>
          <Input
            id="api-url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="http://localhost:8000"
          />
          <p className="text-xs text-muted-foreground">
            All requests will be sent to this base URL.
          </p>
        </div>
        <DialogFooter>
          <Button
            onClick={() => {
              setBaseUrl(url);
              onSaved();
              setOpen(false);
            }}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}