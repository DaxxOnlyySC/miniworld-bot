const BADGE_IDS = [
  "1001", "1002", "1003", "1004", "1005", "1006",
  "1008", "1010", "1011", "1012", "1013", "1014",
  "1015", "1016", "1017", "1018", "1019", "1020"
];

async function generateS7(uin, pwd) {
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(uin + pwd));
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
}

async function unlockBadge(s7, s7t, badgeId) {
  const url = `http://shequ.miniworldgame.com:8080/miniw/achieve?s7=${s7}&s7t=${s7t}`;
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ achieve_id: badgeId, op: 1 }),
      signal: AbortSignal.timeout(10000)
    });
    const text = await resp.text();
    return { badgeId, success: true, response: text };
  } catch (e) {
    return { badgeId, success: false, error: e.message };
  }
}

async function handleRequest(request) {
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };

  if (request.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  const url = new URL(request.url);
  const uin = url.searchParams.get("uin");
  const pwd = url.searchParams.get("pwd");

  if (!uin || !pwd) {
    return Response.json({
      code: 400,
      msg: "Missing uin or pwd"
    }, { headers: corsHeaders });
  }

  const s7 = await generateS7(uin, pwd);
  const s7t = "38ccc";
  let unlocked = 0;
  const errors = [];

  for (const badgeId of BADGE_IDS) {
    const result = await unlockBadge(s7, s7t, badgeId);
    if (result.success) {
      unlocked++;
    } else {
      errors.push(result);
    }
    await new Promise(r => setTimeout(r, 500));
  }

  return Response.json({
    code: 114514,
    msg: "Success",
    unlocked: unlocked,
    total: BADGE_IDS.length,
    errors: errors.length > 0 ? errors : undefined
  }, { headers: corsHeaders });
}

addEventListener("fetch", event => {
  event.respondWith(handleRequest(event.request));
});
