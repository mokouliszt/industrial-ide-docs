import * as React from "react";
import { cn } from "@/lib/utils";
export function Badge({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("inline-flex items-center rounded-sm border border-transparent px-1.5 py-0.5 text-[11px] font-mono font-medium leading-none", className)} {...props} />
  );
}
