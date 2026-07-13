import { useEffect, useMemo, useState } from "react";
import { Command } from "cmdk";
import { useNavigate } from "react-router-dom";
import { Search, FileText } from "lucide-react";
import { loadSearch, SearchDoc, VENDOR_META } from "@/lib/data";
import { cn } from "@/lib/utils";

export function SearchDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const [docs, setDocs] = useState<SearchDoc[]>([]);
  const [query, setQuery] = useState("");
  const [vendorFilter, setVendorFilter] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => { if (open) loadSearch().then(setDocs); }, [open]);
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); onOpenChange(!open); }
      if (e.key === "Escape") onOpenChange(false);
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, onOpenChange]);

  const results = useMemo(() => {
    if (!query.trim()) return [];
    const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    return docs
      .filter((d) => !vendorFilter || d.vendor === vendorFilter)
      .map((d) => {
        const hay = `${d.num} ${d.title} ${d.heads.join(" ")} ${d.excerpt}`.toLowerCase();
        if (!terms.every((t) => hay.includes(t))) return null;
        let score = 0;
        for (const t of terms) {
          if (d.title.toLowerCase().includes(t)) score += 10;
          if (d.heads.some((h) => h.toLowerCase().includes(t))) score += 4;
          if (d.num.toLowerCase().includes(t)) score += 6;
        }
        return { d, score };
      })
      .filter((x): x is { d: SearchDoc; score: number } => !!x)
      .sort((a, b) => b.score - a.score)
      .slice(0, 30);
  }, [docs, query, vendorFilter]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-[2px]" onClick={() => onOpenChange(false)}>
      <div className="mx-auto mt-[10vh] w-[min(640px,92vw)]" onClick={(e) => e.stopPropagation()}>
        <Command shouldFilter={false} className="overflow-hidden rounded-lg border border-paper-line bg-paper shadow-2xl">
          <div className="flex items-center gap-2 border-b border-paper-line px-3">
            <Search className="h-4 w-4 shrink-0 text-ink-faint" />
            <Command.Input
              autoFocus value={query} onValueChange={setQuery}
              placeholder="機能・用語で横断検索 (例: RUN中書込み / シミュレータ / 予約語)"
              className="h-12 w-full bg-transparent text-sm outline-none placeholder:text-ink-faint"
            />
          </div>
          <div className="flex gap-1.5 border-b border-paper-line px-3 py-2">
            {[null, "gxworks3", "kvstudio", "sysmac", "common"].map((v) => (
              <button key={v ?? "all"} onClick={() => setVendorFilter(v)}
                className={cn("rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors",
                  vendorFilter === v ? "border-ink bg-ink text-paper" : "border-paper-line text-ink-soft hover:bg-paper-panel")}>
                {v ? VENDOR_META[v].label : "すべて"}
              </button>
            ))}
          </div>
          <Command.List className="max-h-[50vh] overflow-y-auto p-1.5">
            {query && results.length === 0 && (
              <div className="py-8 text-center text-sm text-ink-faint">該当なし — 別の用語をお試しください</div>
            )}
            {results.map(({ d }) => (
              <Command.Item key={`${d.vendor}/${d.slug}`} value={`${d.vendor}/${d.slug}`}
                onSelect={() => { onOpenChange(false); navigate(d.vendor === "common" ? `/common/${d.slug}` : `/${d.vendor}/${d.slug}`); }}
                className="flex cursor-pointer items-start gap-2.5 rounded-md px-2.5 py-2 aria-selected:bg-paper-panel">
                <FileText className={cn("mt-0.5 h-4 w-4 shrink-0", VENDOR_META[d.vendor].accent)} />
                <div className="min-w-0">
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-xs text-ink-faint">{d.num}</span>
                    <span className="truncate text-sm font-medium">{d.title}</span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-2 text-[11px] text-ink-faint">
                    <span className={VENDOR_META[d.vendor].accent}>{VENDOR_META[d.vendor].label}</span>
                    <span className="truncate">{d.excerpt.slice(0, 70)}</span>
                  </div>
                </div>
              </Command.Item>
            ))}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
