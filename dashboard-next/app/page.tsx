"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  Archive,
  ArrowUpRight,
  Bot,
  Building2,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  Clock3,
  Command,
  Copy,
  CornerDownRight,
  Database,
  Download,
  ExternalLink,
  FileText,
  Filter,
  Gauge,
  Inbox,
  Layers3,
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

type LeadStatus = "未確認" | "送信準備" | "フォームなし" | "ファックス候補あり" | "送信済み" | "再送候補";
type Lead = {
  id: number;
  score: number;
  company: string;
  industry: IndustryGenre;
  area: string;
  source: string;
  status: LeadStatus;
  next: string;
  offer: string;
  url?: string;
  mapUrl?: string;
  formUrl?: string;
  fax?: string;
  email?: string;
  address?: string;
  phone?: string;
  latitude?: number;
  longitude?: number;
  summary?: string;
  searchTerms?: string[];
};
type ProposalDraft = {
  leadId: number;
  subject: string;
  message: string;
};
type CopyField = {
  key: string;
  label: string;
  value: string;
  hint?: string;
};
type NavLabel = "受信箱" | "営業候補" | "地図検索" | "提案文" | "送信待ち" | "履歴";
type SavedView = "フォームあり" | "ファックス候補あり" | "再送フォロー" | "地図情報未確認";
type IndustryGenre =
  | "建材・住宅設備"
  | "食品製造・食品卸"
  | "医療機器・医薬品"
  | "電子部品・精密機器"
  | "機械部品・金属加工"
  | "自動車部品"
  | "印刷・紙製品"
  | "アパレル・繊維"
  | "楽器・イベント機材"
  | "化粧品・日用品"
  | "冷凍冷蔵品"
  | "店舗チェーン納品"
  | "通信販売・倉庫出荷"
  | "産業廃棄物・資源"
  | "農産物・花き";

const industryGenres = [
  "すべて",
  "建材・住宅設備",
  "食品製造・食品卸",
  "医療機器・医薬品",
  "電子部品・精密機器",
  "機械部品・金属加工",
  "自動車部品",
  "印刷・紙製品",
  "アパレル・繊維",
  "楽器・イベント機材",
  "化粧品・日用品",
  "冷凍冷蔵品",
  "店舗チェーン納品",
  "通信販売・倉庫出荷",
  "産業廃棄物・資源",
  "農産物・花き",
] satisfies Array<IndustryGenre | "すべて">;

const initialLeads: Lead[] = [];

const nav = [
  { label: "受信箱", icon: Inbox },
  { label: "営業候補", icon: Layers3 },
  { label: "地図検索", icon: Radar },
  { label: "提案文", icon: FileText },
  { label: "送信待ち", icon: Send },
  { label: "履歴", icon: Archive },
] satisfies Array<{ label: NavLabel; icon: typeof Inbox }>;

const savedViews: SavedView[] = ["フォームあり", "ファックス候補あり", "再送フォロー", "地図情報未確認"];

const salesProfile = {
  company: "有限会社翔栄サービス",
  department: "営業担当",
  contact: "原田 裕士",
  phone: "0270-64-2429",
  email: "showeiservice.office@gmail.com",
  address: "〒370-1104 群馬県佐波郡玉村町上福島752",
};

function normalizeIndustry(value: string): IndustryGenre {
  return industryGenres.includes(value as IndustryGenre) && value !== "すべて" ? (value as IndustryGenre) : "自動車部品";
}

function normalizeStatus(value: string): LeadStatus {
  return ["未確認", "送信準備", "フォームなし", "ファックス候補あり", "送信済み", "再送候補"].includes(value)
    ? (value as LeadStatus)
    : "未確認";
}

function deriveLeadStatus(lead: Record<string, unknown>): LeadStatus {
  const status = normalizeStatus(String(lead.status || "未確認"));
  if (status !== "未確認") return status;
  const hasForm = typeof lead.contactUrl === "string" && lead.contactUrl.trim().length > 0;
  const hasEmail = typeof lead.email === "string" && lead.email.trim().length > 0;
  const hasFax = typeof lead.fax === "string" && lead.fax.trim().length > 0;
  if (hasForm || hasEmail) return "送信準備";
  if (hasFax) return "ファックス候補あり";
  return status;
}

function nextActionForStatus(status: LeadStatus) {
  if (status === "送信準備") return "営業文作成";
  if (status === "ファックス候補あり") return "FAX文作成";
  return "連絡先確認";
}

function mergeLeads(incoming: Lead[], current: Lead[]) {
  const existing = new Set(current.map((lead) => `${lead.company}-${lead.area}`));
  const fresh = incoming.filter((lead) => {
    const key = `${lead.company}-${lead.area}`;
    if (existing.has(key)) return false;
    existing.add(key);
    return true;
  });
  return [...fresh, ...current];
}

function isRealContactUrl(url?: string) {
  if (!url) return false;
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    return !host.endsWith("example.jp") && !host.endsWith("example.com");
  } catch {
    return false;
  }
}

function isExternalUrl(url?: string) {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function isGoogleMapUrl(url?: string) {
  if (!url) return false;
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    return host === "google.com" || host.endsWith(".google.com");
  } catch {
    return false;
  }
}

function getCompanySiteUrl(lead: Lead) {
  return isExternalUrl(lead.url) && !isGoogleMapUrl(lead.url) ? lead.url : undefined;
}

function getMapUrl(lead: Lead) {
  if (isExternalUrl(lead.mapUrl)) return lead.mapUrl;
  if (isGoogleMapUrl(lead.url)) return lead.url;
  const query = [lead.company, lead.address || lead.area].filter(Boolean).join(" ");
  return query ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}` : undefined;
}

function getMapEmbedUrl(lead: Lead) {
  const query =
    typeof lead.latitude === "number" && typeof lead.longitude === "number"
      ? `${lead.latitude},${lead.longitude}`
      : [lead.company, lead.address || lead.area].filter(Boolean).join(" ");
  return query ? `https://maps.google.com/maps?q=${encodeURIComponent(query)}&output=embed` : undefined;
}

function openExternalUrl(url?: string) {
  if (!isExternalUrl(url)) return;
  window.open(url, "_blank", "noopener,noreferrer");
}

async function copyText(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

function shortUrl(url?: string) {
  if (!url) return "";
  try {
    const parsed = new URL(url);
    return `${parsed.hostname}${parsed.pathname === "/" ? "" : parsed.pathname}`;
  } catch {
    return url;
  }
}

function csvCell(value: unknown) {
  const text = Array.isArray(value) ? value.join(" / ") : String(value ?? "");
  return `"${text.replace(/"/g, '""')}"`;
}

function buildLeadsCsv(leads: Lead[]) {
  const headers = [
    "ID",
    "会社名",
    "業界",
    "エリア",
    "営業スコア",
    "状態",
    "次の作業",
    "提案内容",
    "取得元",
    "企業サイトURL",
    "Google Map URL",
    "問い合わせフォームURL",
    "メール",
    "FAX",
    "電話番号",
    "住所",
    "緯度",
    "経度",
    "検索キーワード",
    "メモ",
  ];
  const rows = leads.map((lead) => [
    lead.id,
    lead.company,
    lead.industry,
    lead.area,
    lead.score,
    lead.status,
    lead.next,
    lead.offer,
    lead.source,
    getCompanySiteUrl(lead) || lead.url || "",
    getMapUrl(lead) || "",
    lead.formUrl || "",
    lead.email || "",
    lead.fax || "",
    lead.phone || "",
    lead.address || "",
    lead.latitude ?? "",
    lead.longitude ?? "",
    lead.searchTerms || [],
    lead.summary || "",
  ]);
  return [headers, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n");
}

function downloadCsv(filename: string, csv: string) {
  const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function buildProposalDraft(lead: Lead): ProposalDraft {
  const channel = lead.fax ? "ファックス送信用" : lead.formUrl ? "問い合わせフォーム用" : "営業連絡用";
  const strength = lead.industry.includes("自動車")
    ? "工場間輸送や部品納品の定期便化、欠車リスク対策"
    : lead.industry.includes("食品")
      ? "店舗納品や温度帯に応じた定期配送"
      : lead.industry.includes("医療")
        ? "医療機器の安全な定期納品と緊急配送"
        : lead.offer;

  return {
    leadId: lead.id,
    subject: `配送体制のご相談（${channel}）`,
    message: `${lead.company} ご担当者様

突然のご連絡失礼いたします。
有限会社翔栄サービスの原田と申します。

弊社は群馬県を拠点に、定期便・ルート便・スポット便・緊急配送を行っている運送会社です。
貴社の${lead.industry}に関する配送で、${strength}の面でお役に立てる可能性があると思い、ご連絡いたしました。

小ロットの定期配送、工場間輸送、急な増便や欠車時の代替便など、現在の配送体制でお困りの点がございましたら、一度状況を伺えますと幸いです。

ご多忙のところ恐縮ですが、配送のご相談先としてご検討いただけますでしょうか。

有限会社翔栄サービス
担当: 原田 裕士
TEL: 0270-64-2429`,
  };
}

export default function Page() {
  const [leads, setLeads] = useState(initialLeads);
  const [selectedId, setSelectedId] = useState<number | null>(initialLeads[0]?.id ?? null);
  const [activity, setActivity] = useState<string[]>([]);
  const [filter, setFilter] = useState<LeadStatus | "すべて">("すべて");
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [notice, setNotice] = useState("操作した内容がここに表示されます。");
  const [activeMenu, setActiveMenu] = useState<NavLabel>("営業候補");
  const [activeView, setActiveView] = useState<SavedView | "なし">("なし");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIndustry, setSelectedIndustry] = useState<IndustryGenre | "すべて">("すべて");
  const [draftSearchQuery, setDraftSearchQuery] = useState("");
  const [draftIndustry, setDraftIndustry] = useState<IndustryGenre | "すべて">("すべて");
  const [draftArea, setDraftArea] = useState("群馬県");
  const [draftLimit, setDraftLimit] = useState(10);
  const [isCollecting, setIsCollecting] = useState(false);
  const [collectionProgress, setCollectionProgress] = useState(0);
  const [collectionStep, setCollectionStep] = useState("");
  const [proposalDraft, setProposalDraft] = useState<ProposalDraft | null>(null);

  const selectedLead = leads.find((lead) => lead.id === selectedId) ?? leads[0] ?? null;
  const navCounts: Record<NavLabel, number> = {
    受信箱: activity.length,
    営業候補: leads.length,
    地図検索: leads.filter((lead) => lead.source.includes("地図")).length,
    提案文: proposalDraft ? 1 : 0,
    送信待ち: leads.filter((lead) => lead.status === "送信準備").length,
    履歴: leads.filter((lead) => lead.status === "送信済み").length,
  };
  const visibleLeads = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    return leads.filter((lead) => {
      const matchesStatus = filter === "すべて" || lead.status === filter;
      const matchesMenu =
        activeMenu === "営業候補" ||
        activeMenu === "受信箱" ||
        (activeMenu === "地図検索" && lead.source.includes("地図")) ||
        (activeMenu === "提案文" && (lead.status === "送信準備" || lead.status === "再送候補")) ||
        (activeMenu === "送信待ち" && lead.status === "送信準備") ||
        (activeMenu === "履歴" && lead.status === "送信済み");
      const matchesView =
        activeView === "なし" ||
        (activeView === "フォームあり" && Boolean(lead.formUrl)) ||
        (activeView === "ファックス候補あり" && lead.status === "ファックス候補あり") ||
        (activeView === "再送フォロー" && lead.status === "再送候補") ||
        (activeView === "地図情報未確認" && !lead.source.includes("地図"));
      const matchesIndustry = selectedIndustry === "すべて" || lead.industry === selectedIndustry;
      const searchableText = `${lead.company} ${lead.industry} ${lead.area} ${lead.source} ${lead.offer} ${lead.status}`.toLowerCase();
      const matchesSearch = normalizedQuery.length === 0 || searchableText.includes(normalizedQuery);
      return matchesStatus && matchesMenu && matchesView && matchesIndustry && matchesSearch;
    });
  }, [activeMenu, activeView, filter, leads, searchQuery, selectedIndustry]);

  function pushActivity(message: string) {
    setActivity((current) => [message, ...current].slice(0, 6));
    setNotice(message);
  }

  function updateSelectedLead(next: Partial<Lead>) {
    if (!selectedLead) return;
    setLeads((current) => current.map((lead) => (lead.id === selectedId ? { ...lead, ...next } : lead)));
  }

  function runMapLookup() {
    if (!selectedLead) return;
    updateSelectedLead({
      source: "地図掲載サイト",
      status: selectedLead.status === "未確認" ? "送信準備" : selectedLead.status,
    });
    pushActivity(`${selectedLead.company} の地図情報を確認しました。フォームURLは実取得できた場合だけ表示します。`);
  }

  function createProposal() {
    if (!selectedLead) return;
    updateSelectedLead({ status: "送信準備", next: "送信" });
    setProposalDraft(buildProposalDraft(selectedLead));
    pushActivity(`${selectedLead.company} の営業文を作成しました`);
  }

  function markSent() {
    if (!selectedLead) return;
    updateSelectedLead({ status: "送信済み", next: "再送管理" });
    pushActivity(`${selectedLead.company} を送信済みに記録しました`);
  }

  function addLead() {
    const id = Math.max(...leads.map((lead) => lead.id)) + 1;
    const newLead: Lead = {
      id,
      score: 74,
      company: `新規候補 ${id}`,
      industry: selectedIndustry === "すべて" ? "建材・住宅設備" : selectedIndustry,
      area: "群馬県",
      source: "手動追加",
      status: "未確認",
      next: "連絡先確認",
      offer: "定期便・スポット便の提案",
    };
    setLeads((current) => [newLead, ...current]);
    setSelectedId(id);
    pushActivity(`${newLead.company} を追加しました`);
  }

  function exportAllLeadsCsv() {
    if (leads.length === 0) {
      setNotice("CSV出力できる営業候補がまだありません。先に企業検索を実行してください。");
      return;
    }
    const today = new Date().toISOString().slice(0, 10);
    downloadCsv(`showei-sales-leads-${today}.csv`, buildLeadsCsv(leads));
    pushActivity(`${leads.length}件の営業候補をCSVで出力しました`);
  }

  function selectMenu(label: NavLabel) {
    setActiveMenu(label);
    setActiveView("なし");
    setFilter(label === "送信待ち" ? "送信準備" : label === "履歴" ? "送信済み" : "すべて");
    setNotice(`${label} を表示しました。`);
  }

  function selectSavedView(view: SavedView) {
    setActiveView(view);
    setActiveMenu("営業候補");
    setFilter("すべて");
    setNotice(`${view} の候補に絞り込みました。`);
  }

  async function submitSearch() {
    const targetIndustries =
      draftIndustry === "すべて" ? industryGenres.filter((genre): genre is IndustryGenre => genre !== "すべて") : [draftIndustry];
    const progressMessages = [
      "業界キーワードを展開しています",
      "Google Mapの企業情報を収集しています",
      "求人サイトや不要な情報を除外しています",
      "公式サイト・フォーム・FAXを確認しています",
      "重複企業を整理しています",
    ];
    let progressTimer: ReturnType<typeof setInterval> | undefined;

    setSelectedIndustry(draftIndustry);
    setSearchQuery(draftSearchQuery);
    setActiveMenu("営業候補");
    setActiveView("なし");
    setFilter("すべて");
    const conditions = [
      draftIndustry !== "すべて" ? draftIndustry : "全ジャンル",
      draftSearchQuery.trim() ? `キーワード「${draftSearchQuery.trim()}」` : null,
    ].filter(Boolean);
    setIsCollecting(true);
    setCollectionProgress(6);
    setCollectionStep("検索条件を準備しています");
    setNotice(conditions.length ? `${conditions.join("、")} で企業情報を収集しています。` : "企業情報を収集しています。");
    try {
      progressTimer = setInterval(() => {
        setCollectionProgress((current) => {
          const next = Math.min(current + 7, 92);
          const stageIndex = Math.min(Math.floor(next / 20), progressMessages.length - 1);
          setCollectionStep(progressMessages[stageIndex]);
          return next;
        });
      }, 900);
      const response = await fetch("/api/collect-leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry: draftIndustry,
          industries: draftIndustry === "すべて" ? targetIndustries : undefined,
          area: draftArea,
          keyword: draftSearchQuery,
          limit: draftLimit,
        }),
      });
      const data = await response.json();
      const nextId = Math.max(...leads.map((lead) => lead.id), 0) + 1;
      const collected: Lead[] = (data.leads || []).map((lead: Record<string, unknown>, index: number) => {
        const status = deriveLeadStatus(lead);
        return {
          id: nextId + index,
          score: Number(lead.score || 70),
          company: String(lead.name || `収集候補 ${nextId + index}`),
          industry: normalizeIndustry(String(lead.industry || draftIndustry || "自動車部品")),
          area: String(lead.area || draftArea),
          source: String(lead.source || "企業情報収集"),
          status,
          next: String(lead.next || nextActionForStatus(status)),
          offer: String(lead.offer || "定期便・ルート便の提案"),
          url: String(lead.url || ""),
          mapUrl: typeof lead.mapUrl === "string" ? lead.mapUrl : undefined,
          formUrl: typeof lead.contactUrl === "string" ? lead.contactUrl : undefined,
          fax: typeof lead.fax === "string" ? lead.fax : undefined,
          email: typeof lead.email === "string" ? lead.email : undefined,
          address: typeof lead.address === "string" ? lead.address : undefined,
          phone: typeof lead.phone === "string" ? lead.phone : undefined,
          latitude: typeof lead.latitude === "number" ? lead.latitude : undefined,
          longitude: typeof lead.longitude === "number" ? lead.longitude : undefined,
          summary: typeof lead.summary === "string" ? lead.summary : undefined,
          searchTerms: Array.isArray(lead.searchTerms) ? lead.searchTerms.map(String) : undefined,
        };
      });
      setLeads((current) => mergeLeads(collected, current));
      if (collected[0]) setSelectedId(collected[0].id);
      setCollectionProgress(100);
      setCollectionStep(`完了しました。${targetIndustries.length}ジャンルから候補を整理しました。`);
      pushActivity(data.message || `${collected.length}件の企業候補を収集しました`);
    } catch {
      setCollectionProgress(0);
      setCollectionStep("");
      setNotice("企業情報の収集中にエラーが発生しました。APIキーと通信状況を確認してください。");
    } finally {
      if (progressTimer) clearInterval(progressTimer);
      setIsCollecting(false);
    }
  }

  return (
    <main className={cn("min-h-screen bg-background text-foreground", theme)}>
      <div className="flex min-h-screen">
        <Sidebar
          activeMenu={activeMenu}
          activeView={activeView}
          searchQuery={draftSearchQuery}
          selectedIndustry={draftIndustry}
          area={draftArea}
          limit={draftLimit}
          isCollecting={isCollecting}
          navCounts={navCounts}
          onMenuSelect={selectMenu}
          onSavedViewSelect={selectSavedView}
          onSearchChange={setDraftSearchQuery}
          onIndustryChange={setDraftIndustry}
          onAreaChange={setDraftArea}
          onLimitChange={setDraftLimit}
          onSearchSubmit={submitSearch}
        />
        <section className="flex min-w-0 flex-1 flex-col">
          <Topbar
            theme={theme}
            onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
            onAddLead={addLead}
            onExportCsv={exportAllLeadsCsv}
            exportDisabled={leads.length === 0}
          />
          <div className="mx-auto flex w-full max-w-[1480px] flex-1 flex-col gap-5 px-5 py-5 lg:px-7">
            <Header
              activeMenu={activeMenu}
              searchQuery={searchQuery}
              selectedIndustry={selectedIndustry}
              onRunActions={createProposal}
              onFilter={() => {
                setActiveView("なし");
                setFilter(filter === "すべて" ? "送信準備" : "すべて");
              }}
            />
            <Notice text={notice} />
            <CollectionProgress
              active={isCollecting || collectionProgress > 0}
              progress={collectionProgress}
              step={collectionStep}
              industryCount={draftIndustry === "すべて" ? industryGenres.length - 1 : 1}
              limit={draftLimit}
            />
            <KpiGrid leads={leads} />
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(360px,.95fr)]">
              <LeadTable
                leads={visibleLeads}
                selectedId={selectedId}
                filter={filter}
                onFilterChange={setFilter}
                onSelect={setSelectedId}
                onReset={() => {
                  setActiveMenu("営業候補");
                  setActiveView("なし");
                  setFilter("すべて");
                  setSearchQuery("");
                  setSelectedIndustry("すべて");
                  setDraftSearchQuery("");
                  setDraftIndustry("すべて");
                  setDraftArea("群馬県");
                  setDraftLimit(10);
                }}
              />
              {selectedLead ? (
                <CommandPanel
                  lead={selectedLead}
                  draft={proposalDraft?.leadId === selectedLead.id ? proposalDraft : null}
                  onMapLookup={runMapLookup}
                  onCreateProposal={createProposal}
                  onDraftChange={setProposalDraft}
                  onMarkSent={markSent}
                />
              ) : (
                <EmptyState
                  onAddLead={addLead}
                  onResetFilter={() => {
                    setActiveMenu("営業候補");
                    setActiveView("なし");
                    setFilter("すべて");
                  }}
                />
              )}
            </div>
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
              <WorkflowBoard activity={activity} leads={leads} />
              <EmptyState
                onAddLead={addLead}
                onResetFilter={() => {
                  setActiveMenu("営業候補");
                  setActiveView("なし");
                  setFilter("すべて");
                  setSearchQuery("");
                  setSelectedIndustry("すべて");
                  setDraftSearchQuery("");
                  setDraftIndustry("すべて");
                  setDraftArea("群馬県");
                  setDraftLimit(10);
                }}
              />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Sidebar({
  activeMenu,
  activeView,
  searchQuery,
  selectedIndustry,
  area,
  limit,
  isCollecting,
  navCounts,
  onMenuSelect,
  onSavedViewSelect,
  onSearchChange,
  onIndustryChange,
  onAreaChange,
  onLimitChange,
  onSearchSubmit,
}: {
  activeMenu: NavLabel;
  activeView: SavedView | "なし";
  searchQuery: string;
  selectedIndustry: IndustryGenre | "すべて";
  area: string;
  limit: number;
  isCollecting: boolean;
  navCounts: Record<NavLabel, number>;
  onMenuSelect: (label: NavLabel) => void;
  onSavedViewSelect: (view: SavedView) => void;
  onSearchChange: (value: string) => void;
  onIndustryChange: (value: IndustryGenre | "すべて") => void;
  onAreaChange: (value: string) => void;
  onLimitChange: (value: number) => void;
  onSearchSubmit: () => void;
}) {
  return (
    <aside className="flex w-[248px] shrink-0 flex-col border-r border-border bg-black/20 lg:w-[264px]">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <div className="flex size-7 items-center justify-center rounded-md bg-primary/16 text-primary ring-1 ring-primary/25">
          <Truck className="size-4" />
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">翔栄 営業管理</div>
          <div className="text-xs text-muted-foreground">営業自動化ワークスペース</div>
        </div>
      </div>
      <div className="flex-1 space-y-5 px-3 py-4">
        <div className="space-y-2 rounded-lg border border-border bg-muted/20 p-2">
          <label className="block space-y-1.5">
            <span className="px-2 text-xs font-medium text-muted-foreground">業界ジャンル</span>
            <select
              value={selectedIndustry}
              onChange={(event) => onIndustryChange(event.target.value as IndustryGenre | "すべて")}
              className="h-9 w-full rounded-md border border-border bg-background px-2 text-sm text-foreground outline-none"
            >
              {industryGenres.map((genre) => (
                <option key={genre}>{genre}</option>
              ))}
            </select>
            <span className="block px-2 text-[11px] leading-4 text-muted-foreground">
              「すべて」は全ジャンルを一括で検索します。
            </span>
          </label>
          <label className="flex items-center gap-2 rounded-md border border-border bg-background px-2 py-1.5 text-sm">
            <Search className="size-4 text-muted-foreground" />
            <input
              value={searchQuery}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="追加キーワード"
              className="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            />
          </label>
          <label className="block space-y-1.5">
            <span className="px-2 text-xs font-medium text-muted-foreground">検索エリア</span>
            <input
              value={area}
              onChange={(event) => onAreaChange(event.target.value)}
              placeholder="群馬県"
              className="h-9 w-full rounded-md border border-border bg-background px-2 text-sm text-foreground outline-none placeholder:text-muted-foreground"
            />
          </label>
          <label className="block space-y-1.5">
            <span className="px-2 text-xs font-medium text-muted-foreground">取得件数</span>
            <input
              value={limit}
              min={1}
              max={50}
              type="number"
              onChange={(event) => onLimitChange(Number(event.target.value))}
              className="h-9 w-full rounded-md border border-border bg-background px-2 text-sm text-foreground outline-none"
            />
          </label>
          <Button className="w-full bg-red-500 text-white hover:bg-red-400" onClick={onSearchSubmit} disabled={isCollecting}>
            <Search />
            {isCollecting ? "収集中..." : selectedIndustry === "すべて" ? "全ジャンルを一括検索" : "企業情報を収集する"}
          </Button>
        </div>
        <nav className="space-y-1">
          {nav.map((item) => (
            <button
              key={item.label}
              onClick={() => onMenuSelect(item.label)}
              className={cn(
                "flex h-9 w-full items-center gap-2 rounded-md px-2.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
                activeMenu === item.label && "bg-accent text-foreground",
              )}
            >
              <item.icon className="size-4" />
              <span>{item.label}</span>
              {navCounts[item.label] > 0 ? (
                <span className="ml-auto rounded bg-white/[.06] px-1.5 py-0.5 text-[11px] text-muted-foreground">
                  {navCounts[item.label]}
                </span>
              ) : null}
            </button>
          ))}
        </nav>
        <Separator />
        <div>
          <div className="mb-2 px-2 text-xs font-medium text-muted-foreground">保存ビュー</div>
          {savedViews.map((view) => (
            <button
              key={view}
              onClick={() => onSavedViewSelect(view)}
              className={cn(
                "flex h-8 w-full items-center gap-2 rounded-md px-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground",
                activeView === view && "bg-accent text-foreground",
              )}
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
            <span className="text-sm font-medium">文面自動生成</span>
          </div>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            業種、所在地、送信履歴を見ながら、次の営業文を作成します。
          </p>
        </div>
      </div>
    </aside>
  );
}

function Topbar({
  theme,
  onToggleTheme,
  onAddLead,
  onExportCsv,
  exportDisabled,
}: {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  onAddLead: () => void;
  onExportCsv: () => void;
  exportDisabled: boolean;
}) {
  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background/82 px-4 backdrop-blur">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="lg:hidden">
          <PanelLeft />
        </Button>
        <Badge variant="outline" className="hidden gap-1.5 sm:inline-flex">
          <Activity className="size-3" />
          稼働中
        </Badge>
        <div className="hidden items-center gap-2 rounded-md border border-border bg-muted/20 px-2.5 py-1.5 text-sm text-muted-foreground md:flex">
          <Command className="size-4" />
          <span>作業フローをすぐ開く</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={onToggleTheme} aria-label="表示モード切替">
          {theme === "dark" ? <Moon /> : <Sun />}
        </Button>
        <Button variant="outline" size="sm" onClick={onAddLead}>
          <Plus />
          候補を追加
        </Button>
        <Button variant="outline" size="sm" onClick={onExportCsv} disabled={exportDisabled}>
          <Download />
          CSV出力
        </Button>
      </div>
    </header>
  );
}

function Header({
  activeMenu,
  searchQuery,
  selectedIndustry,
  onRunActions,
  onFilter,
}: {
  activeMenu: NavLabel;
  searchQuery: string;
  selectedIndustry: IndustryGenre | "すべて";
  onRunActions: () => void;
  onFilter: () => void;
}) {
  const conditionText = [
    selectedIndustry !== "すべて" ? `業界「${selectedIndustry}」` : null,
    searchQuery ? `キーワード「${searchQuery}」` : null,
  ].filter(Boolean).join("、");

  return (
    <section className="flex flex-col gap-4 rounded-lg border border-border bg-card/55 p-5 shadow-glow lg:flex-row lg:items-center lg:justify-between">
      <div className="min-w-0">
        <div className="mb-3 flex items-center gap-2">
          <Badge variant="default" className="gap-1.5">
            <Zap className="size-3" />
            営業管理OS
          </Badge>
          <Badge variant="outline">実データ連動</Badge>
        </div>
        <h1 className="text-2xl font-semibold tracking-normal text-foreground md:text-3xl">
          {activeMenu === "営業候補" ? "営業スタッフなしで回る、物流営業ダッシュボード" : `${activeMenu}を確認`}
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          {conditionText
            ? `${conditionText}に一致する候補を表示しています。`
            : "地図掲載サイト、問い合わせフォーム、ファックス、メール、送信履歴を一つの作業列に統合します。事務員さんが空き時間に迷わず送信まで進められる管理画面です。"}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Button variant="outline" onClick={onFilter}>
          <Filter />
          送信準備だけ表示
        </Button>
        <Button onClick={onRunActions}>
          <Sparkles />
          次の作業を実行
        </Button>
      </div>
    </section>
  );
}

function Notice({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-primary/20 bg-primary/10 px-4 py-3 text-sm text-primary">
      {text}
    </div>
  );
}

function CollectionProgress({
  active,
  progress,
  step,
  industryCount,
  limit,
}: {
  active: boolean;
  progress: number;
  step: string;
  industryCount: number;
  limit: number;
}) {
  if (!active) return null;
  return (
    <section className="rounded-lg border border-border bg-card/55 p-4 shadow-glow">
      <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="text-sm font-medium text-foreground">
            {progress >= 100 ? "一括検索が完了しました" : "一括検索を実行中"}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {step || "検索状況を確認しています"}
          </div>
        </div>
        <div className="text-xs text-muted-foreground">
          {industryCount}ジャンル / 最大{limit}件
        </div>
      </div>
      <Progress value={progress} className="h-2" />
    </section>
  );
}

function KpiGrid({ leads }: { leads: Lead[] }) {
  const ready = leads.filter((lead) => lead.status === "送信準備" || lead.status === "ファックス候補あり").length;
  const sent = leads.filter((lead) => lead.status === "送信済み").length;
  const formCount = leads.filter((lead) => lead.formUrl).length;
  const kpis = [
    { label: "候補企業", value: String(leads.length), detail: "現在の管理件数", icon: Building2 },
    { label: "送信準備済み", value: String(ready), detail: "フォームまたはファックスあり", icon: CheckCircle2 },
    { label: "フォームあり", value: String(formCount), detail: "すぐ開けます", icon: Send },
    { label: "送信済み", value: String(sent), detail: "履歴に記録済み", icon: MessageSquareText },
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

function LeadTable({
  leads,
  selectedId,
  filter,
  onFilterChange,
  onSelect,
  onReset,
}: {
  leads: Lead[];
  selectedId: number | null;
  filter: LeadStatus | "すべて";
  onFilterChange: (filter: LeadStatus | "すべて") => void;
  onSelect: (id: number) => void;
  onReset: () => void;
}) {
  return (
    <Card className="panel-surface hairline overflow-hidden">
      <CardHeader className="flex-row items-center justify-between border-b border-border pb-3">
        <div>
          <CardTitle>営業候補パイプライン</CardTitle>
          <CardDescription>優先度順。フォーム、ファックス、地図掲載サイトを同じ行で確認できます。</CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={filter}
            onChange={(event) => onFilterChange(event.target.value as LeadStatus | "すべて")}
            className="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground"
          >
            {["すべて", "未確認", "送信準備", "フォームなし", "ファックス候補あり", "送信済み", "再送候補"].map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <Button variant="ghost" size="icon">
            <MoreHorizontal />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid grid-cols-[64px_1.35fr_.95fr_.95fr_1fr_112px_112px] border-b border-border px-4 py-2 text-xs text-muted-foreground">
          <span>点数</span>
          <span>会社名</span>
          <span>業界</span>
          <span>取得元</span>
          <span>提案内容</span>
          <span>状態</span>
          <span>次の作業</span>
        </div>
        {leads.length === 0 ? (
          <div className="flex min-h-[260px] flex-col items-center justify-center px-4 py-12 text-center">
            <div className="flex size-12 items-center justify-center rounded-lg border border-border bg-muted/35">
              <Search className="size-5 text-primary" />
            </div>
            <h3 className="mt-5 text-base font-semibold">条件に合う候補がありません</h3>
            <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
              左の検索欄や保存ビューを変えると、候補企業を絞り込めます。
            </p>
            <Button variant="outline" className="mt-5" onClick={onReset}>
              絞り込みを解除
            </Button>
          </div>
        ) : leads.map((lead) => (
          <button
            key={lead.id}
            onClick={() => onSelect(lead.id)}
            className={cn(
              "grid w-full grid-cols-[64px_1.35fr_.95fr_.95fr_1fr_112px_112px] items-center border-b border-border/70 px-4 py-3 text-left text-sm transition-colors last:border-b-0 hover:bg-white/[.035]",
              selectedId === lead.id && "bg-primary/8",
            )}
          >
            <div className="font-medium text-primary">{lead.score}</div>
            <div className="min-w-0">
              <div className="truncate font-medium">{lead.company}</div>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                <MapPin className="size-3" />
                {lead.area}
              </div>
            </div>
            <div className="truncate text-muted-foreground">{lead.industry}</div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <ExternalLink className="size-4" />
              <span className="truncate">{lead.source}</span>
            </div>
            <div className="truncate text-muted-foreground">{lead.offer}</div>
            <Badge variant={lead.status === "送信準備" ? "success" : lead.status === "フォームなし" ? "warning" : "outline"}>
              {lead.status}
            </Badge>
            <span className="flex items-center gap-1 text-muted-foreground">
              {lead.next}
              <ArrowUpRight className="size-3.5" />
            </span>
          </button>
        ))}
      </CardContent>
    </Card>
  );
}

function CommandPanel({
  lead,
  draft,
  onMapLookup,
  onCreateProposal,
  onDraftChange,
  onMarkSent,
}: {
  lead: Lead;
  draft: ProposalDraft | null;
  onMapLookup: () => void;
  onCreateProposal: () => void;
  onDraftChange: (draft: ProposalDraft) => void;
  onMarkSent: () => void;
}) {
  const steps = [
    { title: "地図掲載サイトアドレスを取得", desc: "地図情報だけの候補から掲載サイトを補完", icon: MapPin, done: lead.source.includes("地図") },
    { title: "フォーム・ファックスを確認", desc: "問い合わせ先を保存", icon: Phone, done: Boolean(isRealContactUrl(lead.formUrl) || lead.fax || lead.email) },
    { title: "営業文面を作成", desc: "フォーム用またはファックス用を選んで生成", icon: Bot, done: lead.status === "送信準備" || lead.status === "送信済み" },
    { title: "送信済みに記録", desc: "送信方法、切り口、メモを履歴化", icon: Clock3, done: lead.status === "送信済み" },
  ];
  const companySiteUrl = getCompanySiteUrl(lead);
  const mapUrl = getMapUrl(lead);
  const mapEmbedUrl = getMapEmbedUrl(lead);
  const recommendedAction = isRealContactUrl(lead.formUrl)
    ? "フォームを開いて、作成した営業文を貼り付けます。送信後は必ず「送信済みにする」を押してください。"
    : lead.email
      ? "メール宛先があります。文面を作成して、メール下書きへ貼り付けます。"
      : lead.fax
        ? "FAX番号があります。FAX用の文面を作成して送付します。"
        : "まず企業サイトかGoogle Mapを開いて、問い合わせ先を確認します。";

  return (
    <Card className="panel-surface hairline">
      <CardHeader className="border-b border-border pb-3">
        <CardTitle>次にやること</CardTitle>
        <CardDescription>{lead.company} の作業を上から進めます。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        {lead.searchTerms?.length ? (
          <div className="rounded-lg border border-border bg-background/35 p-3">
            <div className="text-xs font-medium text-muted-foreground">見つかった検索キーワード</div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {lead.searchTerms.slice(0, 6).map((term) => (
                <Badge key={term} variant="outline">{term}</Badge>
              ))}
            </div>
          </div>
        ) : null}
        {steps.map((item, index) => (
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
        <div className="grid gap-2 sm:grid-cols-3">
          <Button variant="outline" onClick={onMapLookup}>確認済みにする</Button>
          <Button variant="outline" onClick={onCreateProposal}>文面作成</Button>
          <Button onClick={onMarkSent}>送信済みにする</Button>
        </div>
        <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/10 p-3">
          <div className="text-sm font-semibold text-emerald-200">次にやる作業</div>
          <p className="mt-1 text-sm leading-6 text-emerald-50/85">{recommendedAction}</p>
        </div>
        <div className="rounded-lg border border-border bg-background/35 p-3">
          <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-semibold">地図・企業サイト確認</div>
              <p className="mt-1 text-xs text-muted-foreground">
                営業前に場所、建物、公式サイト、フォームを確認できます。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {mapUrl ? (
                <Button variant="outline" size="sm" onClick={() => openExternalUrl(mapUrl)}>
                  Google Mapを開く
                  <ExternalLink />
                </Button>
              ) : (
                <Button variant="outline" size="sm" disabled>地図未取得</Button>
              )}
              {companySiteUrl ? (
                <Button variant="outline" size="sm" onClick={() => openExternalUrl(companySiteUrl)}>
                  企業サイトを開く
                  <ExternalLink />
                </Button>
              ) : (
                <Button variant="outline" size="sm" disabled>企業サイト未取得</Button>
              )}
              {isRealContactUrl(lead.formUrl) ? (
                <Button size="sm" onClick={() => openExternalUrl(lead.formUrl)}>
                  フォームを開く
                  <ExternalLink />
                </Button>
              ) : (
                <Button variant="outline" size="sm" disabled>フォーム未取得</Button>
              )}
            </div>
          </div>
          <div className="mb-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
            <div className="rounded-md border border-border bg-background/40 px-2 py-1.5">
              地図: {mapUrl ? shortUrl(mapUrl) : "未取得"}
            </div>
            <div className="rounded-md border border-border bg-background/40 px-2 py-1.5">
              企業サイト: {companySiteUrl ? shortUrl(companySiteUrl) : "未取得"}
            </div>
            <div className="rounded-md border border-border bg-background/40 px-2 py-1.5">
              フォーム: {isRealContactUrl(lead.formUrl) ? shortUrl(lead.formUrl) : "未取得"}
            </div>
          </div>
          {mapEmbedUrl ? (
            <div className="overflow-hidden rounded-md border border-border bg-muted/20">
              <iframe
                title={`${lead.company} の地図`}
                src={mapEmbedUrl}
                className="h-56 w-full"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
              />
            </div>
          ) : (
            <div className="rounded-md border border-dashed border-border px-3 py-8 text-center text-sm text-muted-foreground">
              地図情報を取得すると、ここに地図プレビューが表示されます。
            </div>
          )}
        </div>
        <FormCopyTemplate lead={lead} draft={draft} />
        {draft ? (
          <div className="rounded-lg border border-primary/25 bg-primary/8 p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold">作成された営業文</div>
                <p className="mt-1 text-xs text-muted-foreground">送信前に内容を確認し、必要に応じて修正できます。</p>
              </div>
              <Badge variant="success">確認待ち</Badge>
            </div>
            <label className="block space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground">件名</span>
              <input
                value={draft.subject}
                onChange={(event) => onDraftChange({ ...draft, subject: event.target.value })}
                className="h-9 w-full rounded-md border border-border bg-background px-2 text-sm text-foreground outline-none"
              />
            </label>
            <label className="mt-3 block space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground">本文</span>
              <textarea
                value={draft.message}
                onChange={(event) => onDraftChange({ ...draft, message: event.target.value })}
                rows={13}
                className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm leading-6 text-foreground outline-none"
              />
            </label>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {isRealContactUrl(lead.formUrl) ? (
                <Button onClick={() => openExternalUrl(lead.formUrl)}>
                  フォームを開く
                  <ExternalLink />
                </Button>
              ) : (
                <Button variant="outline" disabled>フォーム未取得</Button>
              )}
              {lead.fax ? (
                <div className="flex h-9 items-center rounded-md border border-border bg-background px-3 text-sm">
                  送付先: {lead.fax}
                </div>
              ) : (
                <div className="flex h-9 items-center rounded-md border border-border bg-background px-3 text-sm text-muted-foreground">
                  ファックス未取得
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-border bg-background/30 p-4 text-sm text-muted-foreground">
            「文面作成」を押すと、ここに件名と本文が表示されます。
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function FormCopyTemplate({ lead, draft }: { lead: Lead; draft: ProposalDraft | null }) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const proposal = draft ?? buildProposalDraft(lead);
  const fields: CopyField[] = [
    { key: "company", label: "会社名", value: salesProfile.company, hint: "会社名、貴社名、法人名" },
    { key: "department", label: "部署名", value: salesProfile.department, hint: "部署、所属" },
    { key: "contact", label: "担当者名", value: salesProfile.contact, hint: "氏名、お名前" },
    { key: "phone", label: "電話番号", value: salesProfile.phone, hint: "TEL、電話" },
    { key: "email", label: "メールアドレス", value: salesProfile.email, hint: "E-mail、返信先" },
    { key: "address", label: "住所", value: salesProfile.address, hint: "所在地、住所" },
    { key: "subject", label: "件名", value: proposal.subject, hint: "題名、問い合わせ内容" },
    { key: "message", label: "本文", value: proposal.message, hint: "お問い合わせ内容、備考" },
  ];

  async function handleCopy(key: string, value: string) {
    await copyText(value);
    setCopiedKey(key);
    window.setTimeout(() => setCopiedKey(null), 1400);
  }

  const allText = fields.map((field) => `${field.label}: ${field.value}`).join("\n\n");

  return (
    <div className="rounded-lg border border-border bg-background/35 p-3">
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="text-sm font-semibold">フォーム入力テンプレ</div>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            相手先フォームに合わせて、必要な項目だけコピーして貼り付けます。
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => handleCopy("all", allText)}>
          <Copy />
          {copiedKey === "all" ? "コピー済み" : "全部コピー"}
        </Button>
      </div>
      <div className="grid gap-2">
        {fields.map((field) => (
          <div key={field.key} className="grid gap-2 rounded-md border border-border bg-card/45 p-2 sm:grid-cols-[120px_minmax(0,1fr)_96px] sm:items-center">
            <div>
              <div className="text-xs font-medium text-foreground">{field.label}</div>
              {field.hint ? <div className="mt-1 text-[11px] leading-4 text-muted-foreground">{field.hint}</div> : null}
            </div>
            <div className="min-w-0 rounded border border-border bg-background px-2 py-1.5 text-xs leading-5 text-muted-foreground">
              <span className={cn(field.key === "message" ? "line-clamp-4 whitespace-pre-wrap" : "truncate")}>{field.value}</span>
            </div>
            <Button variant="outline" size="sm" onClick={() => handleCopy(field.key, field.value)}>
              <Copy />
              {copiedKey === field.key ? "済み" : "コピー"}
            </Button>
          </div>
        ))}
      </div>
      <div className="mt-3 rounded-md border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-50/85">
        入力後は送信前に、相手先会社名と本文の宛名だけ確認してください。送信したら「送信済みにする」を押すと履歴に残せます。
      </div>
    </div>
  );
}

function WorkflowBoard({ activity, leads }: { activity: string[]; leads: Lead[] }) {
  const total = Math.max(leads.length, 1);
  const mapChecked = leads.filter((lead) => Boolean(getMapUrl(lead)) || lead.source.includes("地図")).length;
  const contactChecked = leads.filter((lead) => Boolean(isRealContactUrl(lead.formUrl) || lead.email || lead.fax)).length;
  const proposalReady = leads.filter((lead) => lead.status === "送信準備" || lead.status === "送信済み").length;
  const sent = leads.filter((lead) => lead.status === "送信済み").length;
  const flow = [
    { label: "地図情報取得", value: Math.round((mapChecked / total) * 100), icon: MapPin },
    { label: "フォーム・ファックス確認", value: Math.round((contactChecked / total) * 100), icon: ClipboardCheck },
    { label: "営業文面作成", value: Math.round((proposalReady / total) * 100), icon: Bot },
    { label: "送信記録", value: Math.round((sent / total) * 100), icon: Database },
  ];

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
              <p className="mt-1 text-xs text-muted-foreground">最後に操作した営業アクション</p>
            </div>
            <Button variant="ghost" size="sm">すべて見る</Button>
          </div>
          <div className="space-y-2">
            {activity.length === 0 ? (
              <div className="rounded-md border border-dashed border-border px-3 py-4 text-sm text-muted-foreground">
                まだ操作履歴はありません。左の検索から候補を集めると、ここに作業内容が残ります。
              </div>
            ) : (
              activity.map((item, index) => (
                <div key={`${item}-${index}`} className="flex items-center gap-3 rounded-md px-2 py-2 hover:bg-white/[.035]">
                  <CornerDownRight className="size-4 text-muted-foreground" />
                  <span className="min-w-0 flex-1 truncate text-sm">{item}</span>
                  <span className="text-xs text-muted-foreground">{index === 0 ? "いま" : `${index * 12}分前`}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyState({ onAddLead, onResetFilter }: { onAddLead: () => void; onResetFilter: () => void }) {
  return (
    <Card className="panel-surface hairline flex min-h-[360px] flex-col">
      <CardHeader className="border-b border-border pb-3">
        <CardTitle>送信待ちがありません</CardTitle>
        <CardDescription>条件に合う候補がない時も、次の作業へ進めます。</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col items-center justify-center p-8 text-center">
        <div className="flex size-12 items-center justify-center rounded-lg border border-border bg-muted/35">
          <Gauge className="size-5 text-primary" />
        </div>
        <h3 className="mt-5 text-base font-semibold">次の営業候補を準備しましょう</h3>
        <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
          地図検索から会社サイトのアドレスを補完し、フォームまたはファックス候補が見つかった会社だけを送信待ちに追加します。
        </p>
        <div className="mt-5 flex items-center gap-2">
          <Button onClick={onAddLead}>
            <Search />
            候補を追加
          </Button>
          <Button variant="outline" onClick={onResetFilter}>
            <Settings2 />
            絞り込み解除
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
