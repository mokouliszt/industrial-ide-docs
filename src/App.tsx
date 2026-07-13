import { useEffect, useState } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Menu, Search, X } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { SearchDialog } from "@/components/SearchDialog";
import { DocPage } from "@/components/DocPage";
import { TopPage } from "@/components/TopPage";
import { Button } from "@/components/ui/button";
import { loadNav, Nav } from "@/lib/data";

export default function App({ router = true }: { router?: boolean }) {
  if (!router) return <Shell />;
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Shell />
    </BrowserRouter>
  );
}

function Shell() {
  const [nav, setNav] = useState<Nav | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { loadNav().then(setNav); }, []);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-40 border-b border-paper-line bg-paper/90 backdrop-blur">
        <div className="flex h-12 items-center gap-2 px-3 md:px-5">
          <Button variant="ghost" size="icon" className="md:hidden" aria-label="メニュー"
            onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          <Link to="/" className="flex items-baseline gap-2" onClick={() => setMenuOpen(false)}>
            <span className="font-mono text-sm font-semibold tracking-tight">Industrial IDE Docs</span>
            <span className="hidden text-[11px] text-ink-faint sm:inline">GX Works3 / KV STUDIO / Sysmac Studio</span>
          </Link>
          <div className="ml-auto">
            <Button variant="outline" size="sm" onClick={() => setSearchOpen(true)} className="gap-2 text-ink-faint">
              <Search className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">横断検索</span>
              <kbd className="hidden rounded border border-paper-line bg-paper-panel px-1 font-mono text-[10px] sm:inline">⌘K</kbd>
            </Button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1400px]">
        <aside className={
          "fixed inset-y-0 left-0 z-30 w-72 overflow-y-auto border-r border-paper-line bg-paper px-3 pt-16 transition-transform md:sticky md:top-12 md:h-[calc(100vh-3rem)] md:translate-x-0 md:pt-4 " +
          (menuOpen ? "translate-x-0" : "-translate-x-full")
        }>
          {nav && <Sidebar nav={nav} onNavigate={() => setMenuOpen(false)} />}
        </aside>
        {menuOpen && <div className="fixed inset-0 z-20 bg-ink/20 md:hidden" onClick={() => setMenuOpen(false)} />}
        <main className="min-w-0 flex-1">
          <Routes>
            <Route path="/" element={<TopPage />} />
            <Route path="/:vendor/:slug" element={<DocPage />} />
          </Routes>
        </main>
      </div>
      <SearchDialog open={searchOpen} onOpenChange={setSearchOpen} />
    </div>
  );
}
