import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, ArrowRight, BookOpen, ExternalLink } from "lucide-react";
import { loadMarkdown, loadNav, Nav, PageMeta, VENDOR_META } from "@/lib/data";
import { usePreload } from "@/lib/preload";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";


const MdImage = ({ node, src, alt, ...rest }: any) => {
  const url = src && !/^https?:|^\//.test(src) ? import.meta.env.BASE_URL + src : src;
  return (
    <a href={url} target="_blank" rel="noreferrer">
      <img {...rest} src={url} loading="lazy" decoding="async" className="doc-figure" alt={alt ?? "図"} />
    </a>
  );
};

const CAT_LABELS: Record<string, string> = {
  setup: "導入・画面・基本操作", project: "プロジェクト管理", hardware: "ハードウェア構成・パラメータ",
  variables: "変数・デバイス", programming: "プログラミング", transfer: "接続・転送",
  debug: "モニタ・デバッグ・シミュレーション", maintenance: "保守・セキュリティ・運用", reference: "リファレンス・付録",
};

export function DocPage() {
  const { vendor = "common", slug = "index" } = useParams();
  const pre = usePreload();
  const isPre = pre?.page?.vendor === vendor && pre?.page?.slug === slug;

  const [md, setMd] = useState<string | null>(isPre ? pre!.page!.md : null);
  const [nav, setNav] = useState<Nav | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!(pre?.page?.vendor === vendor && pre?.page?.slug === slug)) {
      setMd(null); setError(false);
      loadMarkdown(vendor, slug).then(setMd).catch(() => setError(true));
    }
    loadNav().then(setNav).catch(() => {});
    window.scrollTo(0, 0);
  }, [vendor, slug]);

  const meta: PageMeta | undefined =
    nav?.pages.find((p) => p.vendor === vendor && p.slug === slug) ??
    (isPre ? (pre!.page as PageMeta) : undefined);

  useEffect(() => {
    if (meta) document.title = `${meta.num ? meta.num + " " : ""}${meta.title} | ${VENDOR_META[vendor]?.label ?? ""} | Industrial IDE Docs`;
  }, [meta, vendor]);

  const vm = VENDOR_META[vendor] ?? VENDOR_META.common;
  const cat = meta?.cat ?? (vendor === "common" ? slug : undefined);
  const catLabel = cat ? CAT_LABELS[cat] : undefined;

  // 前後ナビ: nav があれば nav から、なければプリロードから
  let prev: PageMeta | null | undefined, next: PageMeta | null | undefined;
  if (nav && vendor !== "common") {
    const list = nav.pages.filter((p) => p.vendor === vendor);
    const i = list.findIndex((p) => p.slug === slug);
    prev = i > 0 ? list[i - 1] : null;
    next = i >= 0 && i < list.length - 1 ? list[i + 1] : null;
  } else if (isPre) { prev = pre!.prev; next = pre!.next; }

  // 共通カテゴリページ: 3社の該当節リスト
  let catPages: PageMeta[] | undefined;
  if (vendor === "common" && slug !== "index") {
    catPages = nav ? nav.pages.filter((p) => p.cat === slug) : (isPre ? pre!.catPages : undefined);
  }

  if (error) return (
    <div className="mx-auto max-w-3xl px-6 py-16 text-center">
      <p className="text-lg font-medium">ページが見つかりません</p>
      <Link to="/" className="mt-4 inline-block text-sm underline">トップへ戻る</Link>
    </div>
  );

  return (
    <article className="relative mx-auto max-w-3xl px-5 pb-24 pt-8 md:px-8">
      <div className={cn("absolute left-0 top-8 bottom-8 hidden w-[3px] rounded-full opacity-60 md:block", vm.accent)}
        style={{ background: "linear-gradient(to bottom, currentColor 0%, currentColor 55%, transparent 100%)" }} aria-hidden />
      <header className="mb-6 border-b border-paper-line pb-5">
        <nav aria-label="パンくず" className="mb-2 flex flex-wrap items-center gap-2">
          <Link to="/"><Badge className="bg-paper-panel text-ink-soft hover:bg-paper-line">Industrial IDE Docs</Badge></Link>
          <Badge className={cn(vm.soft, vm.accent)}>{vm.label}</Badge>
          {catLabel && cat && vendor !== "common" && (
            <Link to={`/common/${cat}`} className="text-[11px] text-ink-faint underline-offset-2 hover:underline">
              {catLabel} — 3社対応表を見る
            </Link>
          )}
        </nav>
        {md === null && <div className="h-8 w-2/3 animate-pulse rounded bg-paper-panel" />}
      </header>

      {md === null ? (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => <div key={i} className="h-4 animate-pulse rounded bg-paper-panel" style={{ width: `${90 - i * 8}%` }} />)}
        </div>
      ) : (
        <div className="doc-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ img: MdImage }}>{md}</ReactMarkdown>
        </div>
      )}

      {catPages && catPages.length > 0 && (
        <section className="mt-10">
          <h2 className="mb-3 border-b border-paper-line pb-1.5 text-[17px] font-bold">この分類の全節</h2>
          <div className="grid gap-5 md:grid-cols-3">
            {(["gxworks3", "kvstudio", "sysmac"] as const).map((v) => (
              <div key={v}>
                <div className={cn("mb-1.5 text-sm font-semibold", VENDOR_META[v].accent)}>{VENDOR_META[v].label}</div>
                <ul className="space-y-1">
                  {catPages!.filter((p) => p.vendor === v).map((p) => (
                    <li key={p.slug}>
                      <Link to={`/${v}/${p.slug}`} className="text-[12.5px] leading-5 text-ink-soft underline-offset-2 hover:underline">
                        <span className="mr-1 font-mono text-[11px] text-ink-faint">{p.num}</span>{p.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {(prev || next) && (
        <nav aria-label="前後の節" className="mt-12 grid grid-cols-2 gap-3">
          {prev ? (
            <Link to={`/${vendor}/${prev.slug}`} className="group rounded-md border border-paper-line p-3 hover:bg-paper-panel">
              <div className="flex items-center gap-1 text-[11px] text-ink-faint"><ArrowLeft className="h-3 w-3" />前の節</div>
              <div className="mt-1 truncate text-[13px] font-medium"><span className="mr-1 font-mono text-[11px] text-ink-faint">{prev.num}</span>{prev.title}</div>
            </Link>
          ) : <span />}
          {next ? (
            <Link to={`/${vendor}/${next.slug}`} className="group rounded-md border border-paper-line p-3 text-right hover:bg-paper-panel">
              <div className="flex items-center justify-end gap-1 text-[11px] text-ink-faint">次の節<ArrowRight className="h-3 w-3" /></div>
              <div className="mt-1 truncate text-[13px] font-medium"><span className="mr-1 font-mono text-[11px] text-ink-faint">{next.num}</span>{next.title}</div>
            </Link>
          ) : <span />}
        </nav>
      )}

      {md !== null && vendor !== "common" && (
        <footer className="mt-10 rounded-md border border-paper-line bg-paper-panel/60 px-4 py-3 text-[12px] leading-5 text-ink-faint">
          <BookOpen className="mr-1.5 inline h-3.5 w-3.5 align-[-2px]" />
          本ページは元マニュアルの該当節を機械抽出・再構成したものです(図は元PDFから切り出し)。
          抽出漏れや厳密な確認が必要な場合は各社の元マニュアルを参照してください。
          <a className="ml-1 inline-flex items-center gap-0.5 underline underline-offset-2" href={`${import.meta.env.BASE_URL}content/${vendor}/${slug}.md`}>
            Markdown原文 <ExternalLink className="h-3 w-3" />
          </a>
        </footer>
      )}
    </article>
  );
}
