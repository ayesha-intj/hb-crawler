import type { ComponentType, ReactNode, SVGProps } from "react";

type Tone = "neutral" | "accent" | "success";

const TONES: Record<Tone, string> = {
  neutral: "border-white/[0.08] bg-white/[0.03] text-zinc-300",
  accent: "border-indigo-300/15 bg-indigo-300/[0.07] text-indigo-200",
  success: "border-emerald-300/15 bg-emerald-300/[0.07] text-emerald-200",
};

export function Badge({
  icon: Icon,
  children,
  tone = "neutral",
  label,
}: {
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  children: ReactNode;
  tone?: Tone;
  label: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium ${TONES[tone]}`}
    >
      <Icon className="size-3.5 shrink-0 opacity-70" />
      <span className="sr-only">{label}: </span>
      {children}
    </span>
  );
}
