import { NextResponse } from "next/server";
import { readFileSync } from "node:fs";
import { join } from "node:path";

type CollectRequest = {
  industry?: string;
  industries?: string[];
  area?: string;
  keyword?: string;
  limit?: number;
};
type CollectedLead = {
  name: string;
  industry: string;
  area: string;
  url: string;
  mapUrl: string;
  source: string;
  status: string;
  score: number;
  next: string;
  offer: string;
  address: string;
  phone: string;
  latitude: unknown;
  longitude: unknown;
  summary: string;
  searchTerms: string[];
  contactUrl?: string;
  email?: string;
  fax?: string;
};

const excludedDomains = [
  "baseconnect.in",
  "doda.jp",
  "job.mynavi.jp",
  "job.rikunabi.com",
  "indeed.com",
  "jp.indeed.com",
  "求人ボックス.com",
  "stanby.com",
  "townwork.net",
  "baitoru.com",
  "hellowork.mhlw.go.jp",
  "ipros.com",
  "compalyze.co.jp",
  "buffett-code.com",
  "wikipedia.org",
  "x.com",
  "twitter.com",
  "showei-service.com",
];

const excludedWords = [
  "求人",
  "採用",
  "転職",
  "アルバイト",
  "パート",
  "派遣",
  "評判",
  "年収",
  "口コミ",
  "企業一覧",
  "企業情報",
  "Baseconnect",
  "Indeed",
  "マイナビ",
  "リクナビ",
  "doda",
];

const industryTerms: Record<string, string[]> = {
  "建材・住宅設備": ["建材 製造", "建材 工場", "住宅設備 メーカー", "建築資材 卸"],
  "食品製造・食品卸": ["食品工場", "食品製造", "食品卸", "飲料 工場"],
  "医療機器・医薬品": ["医療機器 販売", "医療機器 卸", "医薬品 卸", "介護用品 卸"],
  "電子部品・精密機器": ["電子部品 製造", "精密機器 工場", "基板 実装", "電子部品 卸"],
  "機械部品・金属加工": ["機械部品 製造", "金属加工 工場", "切削加工", "産業機械 部品"],
  "自動車部品": ["自動車部品 製造", "自動車部品 工場", "自動車部品 加工", "自動車部品 サプライヤー", "プレス加工 自動車部品"],
  "印刷・紙製品": ["印刷会社 工場", "紙製品 製造", "パッケージ 印刷", "段ボール 製造"],
  "アパレル・繊維": ["アパレル 倉庫", "繊維 製造", "縫製 工場", "衣料品 卸"],
  "楽器・イベント機材": ["楽器 店舗", "イベント機材 レンタル", "音響機材", "舞台機材"],
  "化粧品・日用品": ["化粧品 製造", "日用品 卸", "生活雑貨 卸", "化粧品 工場"],
  "冷凍冷蔵品": ["冷凍食品 工場", "冷蔵食品 卸", "チルド 食品", "低温物流 荷主"],
  "店舗チェーン納品": ["店舗チェーン 本部", "外食チェーン 物流", "小売チェーン 納品", "ドラッグストア 物流"],
  "通信販売・倉庫出荷": ["通販 倉庫", "EC 出荷", "物流センター 荷主", "倉庫 出荷代行"],
  "産業廃棄物・資源": ["産業廃棄物 処理", "資源 リサイクル", "金属スクラップ", "廃棄物 収集"],
  "農産物・花き": ["農産物 卸", "青果 卸", "花き 卸", "農業法人 出荷"],
};

const allIndustries = Object.keys(industryTerms);

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as CollectRequest;
  const apiKey = getSetting("SERPER_API_KEY");
  const area = body.area || "群馬県";
  const keyword = body.keyword?.trim() || "";
  const limit = Math.min(Math.max(Number(body.limit || 10), 1), 50);
  const industries = resolveIndustries(body);

  if (!apiKey) {
    return NextResponse.json(
      {
        ok: false,
        message: "SERPER_API_KEY が未設定です。Streamlit Cloudまたはローカル環境に設定すると実在企業を収集できます。",
        searchedIndustries: industries,
        leads: sampleLeads(industries, area, limit),
      },
      { status: 200 },
    );
  }

  const searchPlans = industries.flatMap((industry) => buildQueries(industry, area, keyword).map((query) => ({ industry, query })));
  const collected = new Map<string, CollectedLead>();

  for (const { industry, query } of searchPlans) {
    const places = await searchPlaces(apiKey, query, 20);
    for (const place of places) {
      const lead = normalizePlace(place, industry, area, query);
      if (!lead || isExcluded(lead.name, lead.summary || "", lead.url || "")) continue;
      const key = `${lead.name}-${lead.address || lead.url || ""}`;
      const existing = collected.get(key);
      if (existing) {
        existing.searchTerms = Array.from(new Set([...existing.searchTerms, query]));
        existing.score = Math.min(100, existing.score + 2);
        continue;
      }
      collected.set(key, lead);
    }
  }

  const leads = Array.from(collected.values())
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  for (const lead of leads) {
    if (lead.url && /^https?:\/\//.test(lead.url) && !lead.url.includes("google.com/maps")) {
      const contact = await inspectContact(lead.url);
      lead.contactUrl = contact.contactUrl;
      lead.email = contact.email;
      lead.fax = contact.fax;
      if (lead.contactUrl || lead.email) {
        lead.status = "送信準備";
        lead.next = "営業文作成";
      } else if (lead.fax) {
        lead.status = "ファックス候補あり";
        lead.next = "FAX文作成";
      }
    }
  }

  return NextResponse.json({
    ok: true,
    message: `全${industries.length}ジャンル、${searchPlans.length}個の検索キーワードを調査し、${leads.length}件の企業候補を収集しました。`,
    searchedIndustries: industries,
    searchedKeywords: searchPlans.map((plan) => plan.query),
    totalCandidates: collected.size,
    leads,
  });
}

function resolveIndustries(body: CollectRequest) {
  if (Array.isArray(body.industries) && body.industries.length > 0) {
    const validIndustries = Array.from(new Set(body.industries.filter((industry) => industryTerms[industry])));
    return validIndustries.length > 0 ? validIndustries : allIndustries;
  }
  if (!body.industry || body.industry === "すべて") return allIndustries;
  return industryTerms[body.industry] ? [body.industry] : ["自動車部品"];
}

function getSetting(name: string) {
  if (process.env[name]) return process.env[name];
  try {
    const envText = readFileSync(join(process.cwd(), "..", ".env"), "utf8");
    const line = envText.split(/\r?\n/).find((entry) => entry.trim().startsWith(`${name}=`));
    return line?.split("=").slice(1).join("=").trim().replace(/^["']|["']$/g, "");
  } catch {
    return undefined;
  }
}

function buildQueries(industry: string, area: string, keyword: string) {
  const terms = industryTerms[industry] || [industry];
  const selectedTerms = keyword ? [keyword, ...terms] : terms;
  return Array.from(new Set(selectedTerms.map((term) => `${area} ${term} 会社 工場 -求人 -採用 -転職 -アルバイト`)));
}

async function searchPlaces(apiKey: string, query: string, limit: number) {
  const response = await fetch("https://google.serper.dev/places", {
    method: "POST",
    headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify({ q: query, num: Math.max(limit, 10), gl: "jp", hl: "ja" }),
  });
  if (!response.ok) return [];
  const data = await response.json();
  return Array.isArray(data.places) ? data.places : [];
}

function normalizePlace(place: Record<string, unknown>, industry: string, area: string, query: string): CollectedLead | null {
  const name = String(place.title || "").trim();
  if (!name) return null;
  const website = typeof place.website === "string" ? place.website : "";
  const cid = place.cid ? String(place.cid) : "";
  const mapUrl = cid ? `https://www.google.com/maps?cid=${cid}` : "";
  const url = website || mapUrl;
  const category = String(place.category || "");
  const address = String(place.address || "");
  const phone = String(place.phoneNumber || "");
  return {
    name,
    industry,
    area: address || area,
    url,
    mapUrl,
    source: website ? "地図掲載サイト" : "地図情報",
    status: "未確認",
    score: scoreLead(category, website, phone),
    next: "連絡先確認",
    offer: offerForIndustry(industry),
    address,
    phone,
    latitude: place.latitude,
    longitude: place.longitude,
    summary: [category, address, phone].filter(Boolean).join(" / "),
    searchTerms: [query],
  };
}

function scoreLead(category: string, website: string, phone: string) {
  let score = 70;
  if (website) score += 12;
  if (phone) score += 8;
  if (/製造|工場|卸|部品|機器|資材|食品|加工/.test(category)) score += 10;
  return Math.min(score, 98);
}

function offerForIndustry(industry: string) {
  if (industry.includes("自動車")) return "工場間輸送・定期便・欠車リスク対策";
  if (industry.includes("食品") || industry.includes("冷凍")) return "温度帯に応じた定期配送・店舗納品";
  if (industry.includes("医療")) return "医療機器の安全配送・定期納品";
  if (industry.includes("建材")) return "現場納品・資材配送の定期便化";
  return "定期便・ルート便・スポット便の提案";
}

function isExcluded(title: string, summary: string, url: string) {
  const text = `${title} ${summary} ${url}`.toLowerCase();
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    if (excludedDomains.some((domain) => host === domain || host.endsWith(`.${domain}`))) return true;
  } catch {
    // Google Maps URLなし候補は通す
  }
  return excludedWords.some((word) => text.includes(word.toLowerCase()));
}

async function inspectContact(url: string) {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { "User-Agent": "ShoweiSalesResearch/0.1" },
    });
    clearTimeout(timer);
    if (!response.ok) return {};
    const html = await response.text();
    const contactUrl = findContactUrl(url, html);
    const email = html.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i)?.[0];
    const fax = findFax(html);
    return { contactUrl, email, fax };
  } catch {
    return {};
  }
}

function findContactUrl(baseUrl: string, html: string) {
  const linkMatches = Array.from(html.matchAll(/<a[^>]+href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi));
  const scored = linkMatches
    .map((match) => {
      const href = match[1];
      const text = stripTags(match[2]).toLowerCase();
      const haystack = `${href} ${text}`.toLowerCase();
      let score = 0;
      if (haystack.includes("contact") || haystack.includes("お問い合わせ") || haystack.includes("問合せ")) score += 100;
      if (haystack.includes("inquiry") || haystack.includes("相談") || haystack.includes("見積")) score += 80;
      if (haystack.includes("recruit") || haystack.includes("採用") || haystack.includes("求人")) score -= 200;
      return { href, score };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score);
  if (scored[0]) return new URL(scored[0].href, baseUrl).toString();
  if (/<form[\s>]/i.test(html)) return baseUrl;
  return undefined;
}

function findFax(html: string) {
  const text = stripTags(html).replace(/\s+/g, " ");
  return text.match(/(?:FAX|Fax|fax|ファックス)[：:\s]*([0-9]{2,5}[-\s]?[0-9]{1,4}[-\s]?[0-9]{3,4})/)?.[1]?.replace(/\s+/g, "-");
}

function stripTags(html: string) {
  return html.replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " ");
}

function sampleLeads(industries: string[], area: string, limit: number) {
  return industries
    .slice(0, Math.max(1, limit))
    .map((industry, index) => ({
      name: `${area} ${industry} サンプル工場`,
      industry,
      area,
      url: "",
      mapUrl: "",
      source: "サンプル",
      status: "未確認",
      score: 72,
      next: "APIキー設定",
      offer: offerForIndustry(industry),
      summary: "SERPER_API_KEY 設定後に実在企業を収集します。",
      searchTerms: [`${area} ${industry}`],
      id: index + 1,
    }))
    .slice(0, limit);
}
