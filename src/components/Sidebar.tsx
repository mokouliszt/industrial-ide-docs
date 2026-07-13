import { useMemo, useState } from "react";
import { NavLink, useParams } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { Nav, VENDOR_META } from "@/lib/data";
import { cn } from "@/lib/utils";

export function Sidebar({ nav, onNavigate }: { nav: Nav; onNavigate?: () => void }) {
  const { vendor: activeVendor, slug: activeSlug, cat: activeCat } = useParams();
  const [openVendor, setOpenVendor] = useState<string | null>(activeVendor ?? "common");

  const byVendorCat = useMemo(() => {
    const m = new Map<string, Map<string, typeof nav.pages>>();
    for (const p of nav.pages) {
      if (!m.has(p.vendor)) m.set(p.vendor, new Map());
      const cm = m.get(p.vendor)!;
      if (!cm.has(p.cat)) cm.set(p.cat, []);
      cm.get(p.cat)!.push(p);
    }
    return m;
  }, [nav]);

  return (
    <nav aria-label="ドキュメントナビゲーション" className="flex flex-col gap-1 pb-16 text-sm">
      {/* 共通ガイド */}
      <VendorBlock id="common" open={openVendor === "common"} toggle={() => setOpenVendor(openVendor === "common" ? null : "common")}>
        {nav.categories.map((c) => (
          <NavLink key={c.id} to={`/common/${c.id}`} onClick={onNavigate}
            className={({ isActive }) => cn("block rounded px-2 py-1 text-[13px] text-ink-soft hover:bg-paper-panel",
              isActive && "bg-common-soft font-medium text-common")}>
            {c.label}
          </NavLink>
        ))}
      </VendorBlock>

      {nav.vendors.map((v) => (
        <VendorBlock key={v.id} id={v.id} open={openVendor === v.id}
          toggle={() => setOpenVendor(openVendor === v.id ? null : v.id)}>
          {nav.categories.map((c) => {
            const pages = byVendorCat.get(v.id)?.get(c.id) ?? [];
            if (!pages.length) return null;
            return (
              <CategoryBlock key={c.id} label={c.label}
                defaultOpen={v.id === activeVendor && pages.some((p) => p.slug === activeSlug)}>
                {pages.map((p) => (
                  <NavLink key={p.slug} to={`/${v.id}/${p.slug}`} onClick={onNavigate}
                    className={({ isActive }) => cn(
                      "block truncate rounded px-2 py-[3px] text-[12.5px] leading-5 text-ink-soft hover:bg-paper-panel",
                      isActive && cn("font-medium", VENDOR_META[v.id].soft, VENDOR_META[v.id].accent))}>
                    <span className="mr-1.5 font-mono text-[11px] opacity-60">{p.num}</span>
                    {p.title}
                  </NavLink>
                ))}
              </CategoryBlock>
            );
          })}
        </VendorBlock>
      ))}
    </nav>
  );
}

function VendorBlock({ id, open, toggle, children }: { id: string; open: boolean; toggle: () => void; children: React.ReactNode }) {
  const meta = VENDOR_META[id];
  return (
    <div className="mb-1">
      <button onClick={toggle}
        className="flex w-full items-center gap-1.5 rounded px-1.5 py-1.5 text-left hover:bg-paper-panel">
        <ChevronRight className={cn("h-3.5 w-3.5 text-ink-faint transition-transform", open && "rotate-90")} />
        <span className={cn("h-2 w-2 rounded-[2px] bg-current", meta.accent)} aria-hidden />
        <span className={cn("font-semibold", meta.accent)}>{meta.label}</span>
        <span className="text-[11px] text-ink-faint">{meta.company}</span>
      </button>
      {open && <div className="ml-3 mt-0.5 border-l-2 border-paper-line pl-2">{children}</div>}
    </div>
  );
}

function CategoryBlock({ label, defaultOpen, children }: { label: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(!!defaultOpen);
  return (
    <div className="mb-0.5">
      <button onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1 rounded px-1.5 py-1 text-left text-[12px] font-medium text-ink hover:bg-paper-panel">
        <ChevronRight className={cn("h-3 w-3 text-ink-faint transition-transform", open && "rotate-90")} />
        {label}
      </button>
      {open && <div className="ml-2.5 border-l border-paper-line pl-1.5">{children}</div>}
    </div>
  );
}
