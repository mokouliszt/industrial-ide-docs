import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowRight, Bot, FileText } from "lucide-react";
import { loadMarkdown, loadNav, Nav, VENDOR_META } from "@/lib/data";
import { usePreload } from "@/lib/preload";
import { cn } from "@/lib/utils";

const DEVICE_SAMPLES: Record<string, string> = {
  gxworks3: "X0 / M100 / D200",
  kvstudio: "R000 / MR100 / DM200",
  sysmac: "myInput : BOOL",
};

export function TopPage() {
  const pre = usePreload();
  const isPre = pre?.page?.vendor === "common" && pre?.page?.slug === "index" && pre?.route === "/";
  const [nav, setNav] = useState<Nav | null>(null);
  const [md, setMd] = useState<string | null>(isPre ? pre!.page!.md : null);
  useEffect(() => {
    loadNav().then(setNav);
    if (!isPre) loadMarkdown("common", "index").then(setMd);
    document.title = "Industrial IDE Docs — GX Works3 / KV STUDIO / Sysmac Studio 共通構造リファレンス";
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-5 pb-24 pt-10 md:px-8">
      <section className="mb-10">
        <p className="mb-2 font-mono text-[12px] tracking-widest text-ink-faint">INDUSTRIAL IDE DOCS — CROSS-VENDOR REFERENCE</p>
        <h1 className="text-2xl font-bold leading-snug md:text-3xl">
          Industrial IDE Docs
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-soft">
          三菱電機 GX Works3・キーエンス KV STUDIO・オムロン Sysmac Studio のマニュアルを、
          9つの共通カテゴリに再編。用語の違いは対応表で吸収し、各節は元マニュアルから機械抽出したMarkdownで提供します。
        </p>
      </section>

      <section className="mb-10 grid gap-3 md:grid-cols-3">
        {nav?.vendors.map((v) => {
          const count = nav.pages.filter((p) => p.vendor === v.id).length;
          const vm = VENDOR_META[v.id];
          return (
            <Link key={v.id} to={`/${v.id}/${firstSlug(nav, v.id)}`}
              className={cn("group rounded-lg border border-paper-line bg-paper p-4 transition-shadow hover:shadow-md")}>
              <div className={cn("mb-1 h-1 w-10 rounded-full bg-current", vm.accent)} />
              <div className={cn("text-lg font-bold", vm.accent)}>{v.label}</div>
              <div className="text-[12px] text-ink-faint">{v.company}</div>
              <div className="mt-2 font-mono text-[12px] text-ink-soft">{DEVICE_SAMPLES[v.id]}</div>
              <div className="mt-3 flex items-center justify-between text-[12px] text-ink-faint">
                <span><FileText className="mr-1 inline h-3.5 w-3.5 align-[-2px]" />{count} 節</span>
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </div>
            </Link>
          );
        })}
      </section>

      <section className="mb-10 rounded-lg border border-paper-line bg-paper-panel/50 p-4">
        <div className="flex items-start gap-3">
          <Bot className="mt-0.5 h-5 w-5 shrink-0 text-ink-soft" />
          <div className="text-[13px] leading-6 text-ink-soft">
            <span className="font-semibold text-ink">AIエージェント向け:</span>{" "}
            <a className="font-mono underline underline-offset-2" href={`${import.meta.env.BASE_URL}llms.txt`} target="_blank" rel="noreferrer">/llms.txt</a>{" "}
            に全307節へのMarkdownリンク一覧があります。各ページは{" "}
            <span className="font-mono">content/&lt;vendor&gt;/&lt;slug&gt;.md</span>{" "}
            で直接取得でき、frontmatterに vendor / category / 元マニュアルのページ範囲(source)を持ちます。
          </div>
        </div>
      </section>

      {md && (
        <section className="doc-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{md.replace(/^# .+\n/, "")}</ReactMarkdown>
        </section>
      )}
    </div>
  );
}

function firstSlug(nav: Nav, vendor: string): string {
  const p = nav.pages.find((x) => x.vendor === vendor);
  return p?.slug ?? "index";
}
