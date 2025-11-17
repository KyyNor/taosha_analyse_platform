import Link from "next/link";

const items = [
  { href: "/nlquery", label: "查询" },
  { href: "/agent", label: "Agent" },
  { href: "/metadata/tables", label: "元数据" },
  { href: "/logs", label: "日志" },
  { href: "/favorites", label: "收藏" },
  { href: "/settings", label: "设置" }
];

export default function Header() {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur">
      <div className="mx-auto max-w-7xl px-6 h-14 flex items-center justify-between">
        <Link href="/nlquery" className="font-semibold">淘沙分析平台</Link>
        <nav className="flex items-center gap-4 text-sm">
          {items.map((i) => (
            <Link key={i.href} href={i.href} className="text-muted-foreground hover:text-foreground">
              {i.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}