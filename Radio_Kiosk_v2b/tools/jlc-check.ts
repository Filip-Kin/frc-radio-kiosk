const parts = process.argv.slice(2).length ? process.argv.slice(2) : [
  "LTC4279IS#PBF", "LM74700QDBVRQ1", "LMR33630ADDAR", "TLV7011DBVR", "LM3478MA", "TPS26600PWPR", "AP2112K-3.3TRG1", "ESP32-S3-WROOM-1-N8",
  "SUD50P04-13L", "CSD18540Q5B", "SQ4850EY", "PSMN075-100MSE", "2N7002", "AO4406", "AO3400A",
  "XAL7030-103ME", "SRP7028A-100M", "744771133", "SMAJ28A", "SMAJ58A", "B3100", "1N4148W", "S1B",
  "BX0123", "54602-908LF", "R-RJ45R08P-A004", "PJ-002BH", "XH-2A", "1206 fuse 2A", "1000uF 25V", "47uF 63V", "10uF 50V 1210", "22uF 25V 1210", "4.7uF 100V 1210",
];
for (const kw of parts) {
  try {
    const r = await fetch("https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList", {
      method: "POST", headers: { "content-type": "application/json", "user-agent": "Mozilla/5.0" },
      body: JSON.stringify({ currentPage: 1, pageSize: 3, keyword: kw, searchSource: "search", componentLibraryType: "" }),
    });
    const j: any = await r.json();
    const list = j?.data?.componentPageInfo?.list ?? [];
    if (!list.length) { console.log(`${kw.padEnd(22)} | none`); continue; }
    for (const c of list.slice(0, 2)) {
      const p1 = c.componentPrices?.find((x: any) => x.startNumber === 1)?.productPrice ?? c.componentPrices?.[0]?.productPrice;
      const p10 = c.componentPrices?.find((x: any) => x.startNumber === 10)?.productPrice ?? p1;
      const code = (c.urlSuffix ?? "").split("/").pop();
      console.log(`${kw.padEnd(22)} | ${String(c.componentModelEn ?? c.componentName ?? "").slice(0,26).padEnd(26)} | ${code.padEnd(8)} | ${c.componentLibraryType === "base" ? "BASIC" : "ext  "} | stock ${String(c.stockCount).padStart(6)} | $${p1} / $${p10} | ${String(c.componentSpecificationEn ?? "").slice(0,18)}`);
    }
  } catch (e) { console.log(`${kw.padEnd(22)} | ERR ${String(e).slice(0, 60)}`); }
}
