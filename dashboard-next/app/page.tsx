import {
  Activity,
  Archive,
  ArrowUpRight,
  Bot,
  Building2,
  CheckCircle2,
  ChevronDown,
  Circle,
  ClipboardCheck,
  Clock3,
  Command,
  CornerDownRight,
  Database,
  ExternalLink,
  FileText,
  Filter,
  Gauge,
  Inbox,
  Layers3,
  Mail,
  MapPin,
  MessageSquareText,
  Moon,
  MoreHorizontal,
  PanelLeft,
  Phone,
  Plus,
  Radar,
  Search,
  Send,
  Settings2,
  Sparkles,
  Star,
  Sun,
  Truck,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

const nav = [
  { label: "Inbox", icon: Inbox, count: "12" },
  { label: "Pipeline", icon: Layers3, active: true, count: "48" },
  { label: "Map Finder", icon: Radar },
  { label: "Proposals", icon: FileText },
  { label: "Send Queue", icon: Send, count: "7" },
  { label: "Records", icon: Archive },
];

const leads = [
  {
    score: 96,
    company: "清水建材工業",
    area: "群馬県高崎市",
    channel: "Google Map掲載サイト",
    status: "フォームなし",
    next: "電話確認",
    offer: "建材・残土配送の定期便化",
  },
  {
    score: 92,
    company: "AGF関東 食品工場",
    area: "群馬県太田市",
    channel: "問い合わせフォーム",
    status: "送信準備",
    next: "文面確認",
    offer: "店舗納品・温度帯配送",
  },
  {
    score: 88,
    company: "栗原医療器械店 太田支店",
    area: "群馬県太田市",
    channel: "公式サイト",
    status: "FAX候補あり",
    next: "FAX送付",
    offer: "医療機器の欠車リスク対策",
  },
  {
    score: 81,
    company: "高崎精密部品センター",
    area: "群馬県高崎市",
    channel: "メール",
    status: "再送候補",
    next: "別切り口",
    offer: "工場間輸送・スポット便",
  },
];

const flow = [
  { label: "Google Map情報取得", value: 82, icon: MapPin },
  { label: "フォーム/FAX確認", value: 64, icon: ClipboardCheck },
  { label: "AI文面作成", value: 48, icon: Bot },
  { label: "送信記録", value: 37, icon: Database },
];

const recent = [
  { title: "AGF関東へフォーム送信", time: "4分前", tone: "sent" },
  { title: "清水建材工業の掲載サイトURLを取得", time: "17分前", tone: "map" },
  { title: "栗原医療器械店のFAX候補を保存", time: "31分前", tone: "fax" },
  { title: "求人サイト候補を3件除外", time: "1時間前", tone: "clean" },
];

export default function Page() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <Sidebar />
        <section className="flex min-w-0 flex-1 flex-col">
          <Topbar />
          <div className="mx-auto flex w-full max-w-[1480px] flex-1 flex-col gap-5 px-5 py-5 lg:px-7">
            <Header />
            <KpiGrid />
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(360px,.95fr)]">
              <LeadTable />
              <CommandPanel />
            </div>
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
              <WorkflowBoard />
              <EmptyState />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Sidebar() {
  return (
    <aside className="hidden w-[264px] shrink-0 border-r border-border bg-black/20 lg:flex lg:flex-col">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <div className="flex size-7 items-center justify-center rounded-md bg-primary/16 text-primary ring-1 ring-primary/25">
          <Truck className="size-4" />
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">Showei Command</div>
          <div className="text-xs text-muted-foreground">Sales operations</div>
        </div>
      </div>
      <div className="flex-1 space-y-5 px-3 py-4">
        <div className="rounded-lg border border-border bg-muted/20 p-2">
          <div className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm">
            <Search className="size-4 text-muted-foreground" />
            <span className="text-muted-foreground">Search or command</span>
            <kbd className="ml-auto rounded border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">⌘K</kbd>
          </div>
        </div>
        <nav className="space-y-1">
          {nav.map((item) => (
            <button
              key={item.label}
              className={cn(
                "flex h-9 w-full items-center gap-2 rounded-md px-2.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
                item.active && "bg-accent text-foreground",
              )}
            >
              <item.icon className="size-4" />
              <span>{item.label}</span>
              {item.count ? (
                <span className="ml-auto rounded bg-white/[.06] px-1.5 py-0.5 text-[11px] text-muted-foreground">
                  {item.count}
                </span>
              ) : null}
            </button>
          ))}
        </nav>
        <Separator />
        <div>
          <div className="mb-2 px-2 text-xs font-medium text-muted-foreground">Saved views</div>
          {["フォームあり", "FAX候補あり", "再送フォロー", "Google Map未確認"].map((view) => (
            <button
              key={view}
              className="flex h-8 w-full items-center gap-2 rounded-md px-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
            >
              <Circle className="size-2.5 fill-current" />
              {view}
            </button>
          ))}
        </div>
      </div>
      <div className="border-t border-border p-3">
        <div className="rounded-lg border border-border bg-card p-3">
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            <span className="text-sm font-medium">AI文面生成</span>
          </div>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            業種、所在地、送信履歴を見ながら、次の一手を自動提案します。
          </p>
        </div>
      </div>
    </aside>
  );
}

function Topbar() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background/82 px-4 backdrop-blur">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="lg:hidden">
          <PanelLeft />
        </Button>
        <Badge variant="outline" className="hidden gap-1.5 sm:inline-flex">
          <Activity className="size-3" />
          Live workspace
        </Badge>
        <div className="hidden items-center gap-2 rounded-md border border-border bg-muted/20 px-2.5 py-1.5 text-sm text-muted-foreground md:flex">
          <Command className="size-4" />
          <span>Type to focus a workflow</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" aria-label="Light mode preview">
          <Sun />
        </Button>
        <Button variant="ghost" size="icon" aria-label="Dark mode">
          <Moon />
        </Button>
        <Button variant="outline" size="sm">
          <Plus />
          New lead
        </Button>
      </div>
    </header>
  );
}

function Header() {
  return (
    <section className="flex flex-col gap-4 rounded-lg border border-border bg-card/55 p-5 shadow-glow lg:flex-row lg:items-center lg:justify-between">
      <div className="min-w-0">
        <div className="mb-3 flex items-center gap-2">
          <Badge variant="default" className="gap-1.5">
            <Zap className="size-3" />
            Outreach OS
          </Badge>
          <Badge variant="outline">May 28, 2026</Badge>
        </div>
        <h1 className="text-2xl font-semibold tracking-normal text-foreground md:text-3xl">
          営業スタッフなしで回る、物流営業ダッシュボード
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          Google Map掲載サイト、フォーム、FAX、メール、送信履歴を一つの作業列に統合。事務員さんが空き時間に迷わず送信まで進められる管理画面です。
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Button variant="outline">
          <Filter />
          Filters
        </Button>
        <Button>
          <Sparkles />
          Run next actions
        </Button>
      </div>
    </section>
  );
}

function KpiGrid() {
  const kpis = [
    { label: "候補企業", value: "128", detail: "+18 this week", icon: Building2 },
    { label: "送信準備OK", value: "34", detail: "フォーム/FAXあり", icon: CheckCircle2 },
    { label: "本日の送信", value: "12", detail: "平均2.4分/件", icon: Send },
    { label: "返信・商談化", value: "7", detail: "18.9% response", icon: MessageSquareText },
  ];

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi) => (
        <Card key={kpi.label} className="panel-surface hairline">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">{kpi.label}</div>
              <kpi.icon className="size-4 text-muted-foreground" />
            </div>
            <div className="mt-3 text-3xl font-semibold tracking-normal">{kpi.value}</div>
            <div className="mt-1 text-xs text-muted-foreground">{kpi.detail}</div>
          </CardContent>
        </Card>
      ))}
    </section>
  );
}

function LeadTable() {
  return (
    <Card className="panel-surface hairline overflow-hidden">
      <CardHeader className="flex-row items-center justify-between border-b border-border pb-3">
        <div>
          <CardTitle>営業候補パイプライン</CardTitle>
          <CardDescription>優先度順。フォーム、FAX、Google Map掲載サイトを同じ行で確認できます。</CardDescription>
        </div>
        <Button variant="ghost" size="icon">
          <MoreHorizontal />
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid grid-cols-[72px_1.45fr_1fr_1fr_112px_116px] border-b border-border px-4 py-2 text-xs text-muted-foreground">
          <span>Score</span>
          <span>Company</span>
          <span>Source</span>
          <span>Offer</span>
          <span>Status</span>
          <span>Next</span>
        </div>
        {leads.map((lead) => (
          <div
            key={lead.company}
            className="grid grid-cols-[72px_1.45fr_1fr_1fr_112px_116px] items-center border-b border-border/70 px-4 py-3 text-sm transition-colors last:border-b-0 hover:bg-white/[.035]"
          >
            <div className="font-medium text-primary">{lead.score}</div>
            <div className="min-w-0">
              <div className="truncate font-medium">{lead.company}</div>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                <MapPin className="size-3" />
                {lead.area}
              </div>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <ExternalLink className="size-4" />
              <span className="truncate">{lead.channel}</span>
            </div>
            <div className="truncate text-muted-foreground">{lead.offer}</div>
            <Badge variant={lead.status === "送信準備" ? "success" : lead.status === "フォームなし" ? "warning" : "outline"}>
              {lead.status}
            </Badge>
            <Button variant="ghost" size="sm" className="justify-start px-2">
              {lead.next}
              <ArrowUpRight className="ml-auto" />
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function CommandPanel() {
  return (
    <Card className="panel-surface hairline">
      <CardHeader className="border-b border-border pb-3">
        <CardTitle>次にやること</CardTitle>
        <CardDescription>空き時間に上から処理できる、迷わない営業フロー。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        {[
          { title: "Google Map掲載サイトURLを取得", desc: "CIDのみの候補から公式/掲載サイトを補完", icon: MapPin, done: true },
          { title: "フォーム・FAXを確認", desc: "問い合わせフォーム、FAX、電話候補を保存", icon: Phone, done: true },
          { title: "AI文面を作成", desc: "フォーム用またはFAX用を選んで生成", icon: Bot, done: false },
          { title: "送信済みに記録", desc: "送信方法、切り口、メモを履歴化", icon: Clock3, done: false },
        ].map((item, index) => (
          <div key={item.title} className="flex gap-3 rounded-lg border border-border bg-background/35 p-3">
            <div className={cn("flex size-8 shrink-0 items-center justify-center rounded-md", item.done ? "bg-emerald-500/12 text-emerald-300" : "bg-primary/12 text-primary")}>
              <item.icon className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{index + 1}. {item.title}</span>
                {item.done ? <Badge variant="success">完了</Badge> : <Badge variant="outline">これから</Badge>}
              </div>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.desc}</p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function WorkflowBoard() {
  return (
    <Card className="panel-surface hairline">
      <CardHeader className="border-b border-border pb-3">
        <CardTitle>オペレーション進捗</CardTitle>
        <CardDescription>事務作業の詰まりを見える化します。</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 p-4 md:grid-cols-2">
        {flow.map((item) => (
          <div key={item.label} className="rounded-lg border border-border bg-background/35 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium">
                <item.icon className="size-4 text-primary" />
                {item.label}
              </div>
              <span className="text-sm text-muted-foreground">{item.value}%</span>
            </div>
            <Progress value={item.value} className="mt-4" />
          </div>
        ))}
        <div className="rounded-lg border border-border bg-background/35 p-4 md:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">最近の処理</div>
              <p className="mt-1 text-xs text-muted-foreground">チームが最後に触った営業アクション</p>
            </div>
            <Button variant="ghost" size="sm">View all</Button>
          </div>
          <div className="space-y-2">
            {recent.map((item) => (
              <div key={item.title} className="flex items-center gap-3 rounded-md px-2 py-2 hover:bg-white/[.035]">
                <CornerDownRight className="size-4 text-muted-foreground" />
                <span className="min-w-0 flex-1 truncate text-sm">{item.title}</span>
                <span className="text-xs text-muted-foreground">{item.time}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyState() {
  return (
    <Card className="panel-surface hairline flex min-h-[360px] flex-col">
      <CardHeader className="border-b border-border pb-3">
        <CardTitle>送信待ちがありません</CardTitle>
        <CardDescription>条件に合う候補がない時も、画面が行き止まりにならない空状態。</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col items-center justify-center p-8 text-center">
        <div className="flex size-12 items-center justify-center rounded-lg border border-border bg-muted/35">
          <Gauge className="size-5 text-primary" />
        </div>
        <h3 className="mt-5 text-base font-semibold">次の営業候補を準備しましょう</h3>
        <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
          Google Map検索から会社URLを補完し、フォームまたはFAX候補が見つかった会社だけを送信キューに追加します。
        </p>
        <div className="mt-5 flex items-center gap-2">
          <Button>
            <Search />
            候補を検索
          </Button>
          <Button variant="outline">
            <Settings2 />
            条件を調整
          </Button>
        </div>
        <div className="mt-6 flex items-center gap-2 text-xs text-muted-foreground">
          <Star className="size-3.5 text-amber-300" />
          推奨: 建材、医療器械、食品、電子部品から始める
        </div>
      </CardContent>
    </Card>
  );
}
