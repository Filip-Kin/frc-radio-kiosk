// BOM from the board's footprint properties, priced from JLC's library at the 5-board tier
const pcb = await Bun.file("/media/nas/filip/ncdata/filip/files/Electronics/loon-projects/Radio_Kiosk_v2b/board.kicad_pcb").text();
const rows: { ref: string; value: string; code: string | null; pads: number }[] = [];
for (const m of pcb.matchAll(/\n\t\(footprint "[^"]*"\n[\s\S]*?\n\t\)/g)) {
  const b = m[0]; const g = (n: string) => b.match(new RegExp(`\\(property "${n}" "([^"]*)"`))?.[1] ?? null;
  const ref = g("Reference") ?? ""; if (!ref || ref.startsWith("H")) continue;
  rows.push({ ref, value: g("Value") ?? "", code: g("LCSC"), pads: (b.match(/\n\t\t\(pad "/g) ?? []).length });
}
const codes = [...new Set(rows.map((r) => r.code).filter(Boolean))] as string[];
const cache: Record<string, any> = JSON.parse(await Bun.file("/home/filip/tmp/jlc-prices.json").text());
for (const code of codes) {
  if (cache[code] && !cache[code].none) continue;
  const r = await fetch("https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList", { method: "POST", headers: { "content-type": "application/json", "user-agent": "Mozilla/5.0" }, body: JSON.stringify({ currentPage: 1, pageSize: 3, keyword: code, searchSource: "search", componentLibraryType: "" }) });
  const j: any = await r.json(); const list = j?.data?.componentPageInfo?.list ?? [];
  const c = list.find((x: any) => (x.urlSuffix ?? "").endsWith("/" + code)) ?? list[0];
  cache[code] = c ? { name: c.componentModelEn, basic: c.componentLibraryType === "base", stock: c.stockCount, prices: (c.componentPrices ?? []).map((x: any) => [x.startNumber, x.productPrice]) } : { none: true };
}
await Bun.write("/home/filip/tmp/jlc-prices.json", JSON.stringify(cache, null, 1));
const N = 5; let parts = 0, joints = 0; const ext = new Set<string>(), basic = new Set<string>(); const nocode: string[] = [], nostock: string[] = [];
for (const r of rows) {
  joints += r.pads;
  if (!r.code || cache[r.code]?.none) { nocode.push(r.ref); continue; }
  const p = cache[r.code]; const unit = [...p.prices].filter((t: any) => t[0] <= N).pop()?.[1] ?? p.prices[0]?.[1] ?? 0;
  parts += unit; (p.basic ? basic : ext).add(r.code); if (p.stock === 0) nostock.push(`${r.ref} ${p.name}`);
}
console.log(`parts/board $${parts.toFixed(2)} (x5 = $${(parts * N).toFixed(2)}); extended types ${ext.size}; basic types ${basic.size}; no code: ${nocode.join(" ")}; stock 0: ${nostock.join(", ")}; joints ${joints}`);
