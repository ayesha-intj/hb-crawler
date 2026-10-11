// Monogram tile: first letter of the company on a muted colour picked from its name.
const PALETTE = [
  "bg-indigo-400/15 text-indigo-200",
  "bg-sky-400/15 text-sky-200",
  "bg-emerald-400/15 text-emerald-200",
  "bg-amber-400/15 text-amber-200",
  "bg-rose-400/15 text-rose-200",
  "bg-violet-400/15 text-violet-200",
  "bg-teal-400/15 text-teal-200",
];

function colourFor(name: string): string {
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

export function CompanyAvatar({
  name,
  size = "md",
}: {
  name: string;
  size?: "md" | "lg";
}) {
  const letter = name.trim().charAt(0).toUpperCase() || "?";
  const box = size === "lg" ? "size-12 text-lg" : "size-10 text-sm";
  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center rounded-lg font-semibold ring-1 ring-inset ring-white/10 ${box} ${colourFor(name)}`}
    >
      {letter}
    </span>
  );
}
