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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { checkHealth, getBaseUrl, setBaseUrl } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const nav = [
  { to: "/", label: "Dashboard", icon: Home },
  { to: "/sprint-analysis", label: "Sprint Analysis", icon: BarChart3 },
  { to: "/capacity", label: "Capacity Report", icon: Users },
  { to: "/brd", label: "BRD Alignment", icon: FileText },
  { to: "/chat", label: "AI Support Chat", icon: MessageSquare },
] as const;

export function AppShell() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [connected, setConnected] = useState<boolean | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let alive = true;
    checkHealth().then((ok) => alive && setConnected(ok));
    return () => {
      alive = false;
    };
  }, [refreshKey]);

  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <aside className="hidden md:flex w-60 flex-col border-r border-border bg-sidebar">
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
          Capstone · Beko × Bahçeşehir
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 md:px-6">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-sm md:text-base font-semibold truncate">
              BAI — Beko AI Sprint Management
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
  const [url, setUrl] = useState(getBaseUrl());
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
            All requests will be sent to this base URL. Falls back to mock data
            when unreachable.
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