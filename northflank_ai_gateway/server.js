const http = require("http");
const crypto = require("crypto");
const { createDeviceBindingsStoreFromEnv } = require("./device_bindings_store");

const PORT = parseInt(process.env.PORT || "3000", 10);
const ACCESS_TOKEN_TTL_SEC = Math.max(300, parseInt(process.env.ACCESS_TOKEN_TTL_SEC || "604800", 10));
const APP_TOKEN_SECRET = String(process.env.APP_TOKEN_SECRET || "").trim();
const GROQ_API_BASE_URL = String(process.env.GROQ_API_BASE_URL || "https://api.groq.com/openai/v1").trim().replace(/\/+$/, "");
const GROQ_KEY_COOLDOWN_SEC = Math.max(30, parseInt(process.env.GROQ_KEY_COOLDOWN_SEC || "900", 10));
const GROQ_INVALID_KEY_COOLDOWN_SEC = Math.max(60, parseInt(process.env.GROQ_INVALID_KEY_COOLDOWN_SEC || "3600", 10));
const GROQ_NETWORK_ERROR_COOLDOWN_SEC = Math.max(5, parseInt(process.env.GROQ_NETWORK_ERROR_COOLDOWN_SEC || "20", 10));

let groqCursor = 0;
const groqKeyStateMap = new Map();
const bindingsStore = createDeviceBindingsStoreFromEnv(process.env);
const bindingsStoreInfo = bindingsStore.describe();

function nowSeconds() {
  return Math.floor(Date.now() / 1000);
}

function base64Url(input) {
  return Buffer.from(input)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function hmacBase64Url(secret, text) {
  return crypto.createHmac("sha256", secret).update(text).digest("base64url");
}

function sha256Hex(text) {
  return crypto.createHash("sha256").update(text).digest("hex");
}

function stableDeviceKeyHash(deviceKey) {
  return hmacBase64Url(APP_TOKEN_SECRET, String(deviceKey || "").trim());
}

function getGroqKeys() {
  const keys = [];
  const seen = new Set();
  function pushUniqueKey(rawValue, label) {
    const key = String(rawValue || "").trim();
    if (!key || seen.has(key)) {
      return;
    }
    seen.add(key);
    keys.push({
      value: key,
      label: String(label || `key_${keys.length + 1}`),
    });
  }
  const rawList = String(process.env.GROQ_API_KEYS || "").trim();
  if (rawList) {
    let offset = 0;
    for (const part of rawList.split(/[,\s;]+/)) {
      offset += 1;
      pushUniqueKey(part, `GROQ_API_KEYS_${offset}`);
    }
  }
  for (const envName of ["GROQ_API_KEY", "GROQ_KEY_1", "GROQ_KEY_2", "GROQ_KEY_3"]) {
    pushUniqueKey(process.env[envName], envName);
  }
  return keys.map((item, index) => ({ ...item, index }));
}

function keyStateId(keyConfig) {
  return sha256Hex(String((keyConfig || {}).value || ""));
}

function getGroqKeyState(keyConfig) {
  const stateId = keyStateId(keyConfig);
  if (!groqKeyStateMap.has(stateId)) {
    groqKeyStateMap.set(stateId, {
      stateId,
      label: keyConfig.label,
      status: "ready",
      cooldownUntil: 0,
      lastStatusCode: 0,
      lastError: "",
      lastUsedAt: "",
      lastSuccessAt: "",
      lastFailureAt: "",
      successCount: 0,
      failCount: 0,
    });
  }
  return groqKeyStateMap.get(stateId);
}

function markGroqKeySuccess(keyConfig) {
  const state = getGroqKeyState(keyConfig);
  const nowIso = new Date().toISOString();
  state.status = "ready";
  state.cooldownUntil = 0;
  state.lastStatusCode = 200;
  state.lastError = "";
  state.lastUsedAt = nowIso;
  state.lastSuccessAt = nowIso;
  state.successCount += 1;
}

function markGroqKeyFailure(keyConfig, statusCode, errorMessage, cooldownSec) {
  const state = getGroqKeyState(keyConfig);
  const nowIso = new Date().toISOString();
  const cooldownUntil = cooldownSec > 0 ? nowSeconds() + cooldownSec : 0;
  state.status = cooldownUntil > nowSeconds() ? "cooling_down" : "ready";
  state.cooldownUntil = cooldownUntil;
  state.lastStatusCode = Number(statusCode || 0);
  state.lastError = String(errorMessage || "").slice(0, 500);
  state.lastUsedAt = nowIso;
  state.lastFailureAt = nowIso;
  state.failCount += 1;
}

function groqKeyCooldownRemaining(state) {
  const remaining = Math.max(0, Number(state.cooldownUntil || 0) - nowSeconds());
  return remaining;
}

function listGroqKeyHealth() {
  const keys = getGroqKeys();
  return keys.map((keyConfig) => {
    const state = getGroqKeyState(keyConfig);
    const cooldownRemainingSec = groqKeyCooldownRemaining(state);
    return {
      index: keyConfig.index + 1,
      label: keyConfig.label,
      status: cooldownRemainingSec > 0 ? "cooling_down" : "ready",
      cooldown_remaining_sec: cooldownRemainingSec,
      last_status_code: state.lastStatusCode || 0,
      last_error: state.lastError || "",
      last_used_at: state.lastUsedAt || "",
      last_success_at: state.lastSuccessAt || "",
      last_failure_at: state.lastFailureAt || "",
      success_count: state.successCount || 0,
      fail_count: state.failCount || 0,
    };
  });
}

function orderedGroqKeys(keys) {
  const total = keys.length;
  if (!total) {
    return [];
  }
  const startIndex = groqCursor % total;
  const ready = [];
  const cooling = [];
  for (let offset = 0; offset < total; offset += 1) {
    const idx = (startIndex + offset) % total;
    const keyConfig = keys[idx];
    const state = getGroqKeyState(keyConfig);
    if (groqKeyCooldownRemaining(state) > 0) {
      cooling.push(keyConfig);
    } else {
      ready.push(keyConfig);
    }
  }
  return ready.concat(cooling);
}

function sanitizeString(value, maxLen) {
  return String(value || "").trim().slice(0, maxLen);
}

function withCors(headers) {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "authorization,content-type,x-device-id,x-device-key,x-machine-fingerprint",
    ...headers,
  };
}

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, withCors({ "content-type": "application/json; charset=utf-8" }));
  res.end(JSON.stringify(data));
}

function sendText(res, statusCode, text) {
  res.writeHead(statusCode, withCors({ "content-type": "text/plain; charset=utf-8" }));
  res.end(String(text || ""));
}

async function readJsonBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  if (!raw.trim()) {
    return {};
  }
  return JSON.parse(raw);
}

function issueAccessToken(binding) {
  const payload = {
    sub: binding.deviceId,
    dk: binding.deviceKeyHash,
    fp: binding.machineFingerprint,
    iat: nowSeconds(),
    exp: nowSeconds() + ACCESS_TOKEN_TTL_SEC,
  };
  const payloadEncoded = base64Url(JSON.stringify(payload));
  const sig = hmacBase64Url(APP_TOKEN_SECRET, payloadEncoded);
  return `${payloadEncoded}.${sig}`;
}

function verifyAccessToken(token) {
  const raw = String(token || "").trim();
  const parts = raw.split(".");
  if (parts.length !== 2) {
    return { ok: false, error: "invalid_token" };
  }
  const [payloadEncoded, sig] = parts;
  const expected = hmacBase64Url(APP_TOKEN_SECRET, payloadEncoded);
  if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) {
    return { ok: false, error: "invalid_signature" };
  }
  try {
    const payload = JSON.parse(Buffer.from(payloadEncoded, "base64url").toString("utf8"));
    if (!payload || typeof payload !== "object") {
      return { ok: false, error: "invalid_payload" };
    }
    if (Number(payload.exp || 0) <= nowSeconds()) {
      return { ok: false, error: "token_expired" };
    }
    return { ok: true, payload };
  } catch (_error) {
    return { ok: false, error: "invalid_payload" };
  }
}

async function registerDevice(body) {
  const deviceId = sanitizeString(body.device_id, 128);
  const deviceKey = sanitizeString(body.device_key, 256);
  const machineFingerprint = sanitizeString(body.machine_fingerprint, 256);
  const platformName = sanitizeString(body.platform, 256);
  const appId = sanitizeString(body.app_id, 128) || "eduplay-studio";

  if (!deviceId.startsWith("dev_") || deviceId.length < 12) {
    return { status: 400, body: { error: { message: "bad_device_id" } } };
  }
  if (!deviceKey.startsWith("dkey_") || deviceKey.length < 20) {
    return { status: 400, body: { error: { message: "bad_device_key" } } };
  }
  if (!machineFingerprint.startsWith("mfp_") || machineFingerprint.length < 20) {
    return { status: 400, body: { error: { message: "bad_machine_fingerprint" } } };
  }

  const deviceKeyHash = stableDeviceKeyHash(deviceKey);
  const existing = await bindingsStore.getByDeviceId(deviceId);
  let bindingStatus = "registered";
  const currentIso = new Date().toISOString();
  const existingByDeviceKeyHash = await bindingsStore.getByDeviceKeyHash(deviceKeyHash);

  if (existingByDeviceKeyHash && existingByDeviceKeyHash.deviceId !== deviceId) {
    return { status: 403, body: { error: { message: "device_key_already_bound" } } };
  }

  if (existing) {
    const sameBinding =
      existing.deviceKeyHash === deviceKeyHash &&
      existing.machineFingerprint === machineFingerprint;
    if (!sameBinding) {
      return { status: 403, body: { error: { message: "device_binding_mismatch" } } };
    }
    bindingStatus = "known";
  }

  const savedBinding = await bindingsStore.upsertBinding({
    deviceId,
    deviceKeyHash,
    machineFingerprint,
    platform: platformName,
    appId,
    createdAt: existing && existing.createdAt ? existing.createdAt : currentIso,
    lastSeenAt: currentIso,
  });

  return {
    status: 200,
    body: {
      access_token: issueAccessToken(savedBinding),
      binding_status: bindingStatus,
      device_key_accepted: true,
    },
  };
}

async function verifyDeviceHeaders(req) {
  const auth = String(req.headers.authorization || "").trim();
  const deviceId = sanitizeString(req.headers["x-device-id"], 128);
  const deviceKey = sanitizeString(req.headers["x-device-key"], 256);
  const machineFingerprint = sanitizeString(req.headers["x-machine-fingerprint"], 256);

  if (!auth.startsWith("Bearer ")) {
    return { ok: false, status: 401, error: "missing_token" };
  }
  if (!deviceId || !deviceKey || !machineFingerprint) {
    return { ok: false, status: 401, error: "missing_device_headers" };
  }

  const tokenCheck = verifyAccessToken(auth.slice("Bearer ".length));
  if (!tokenCheck.ok) {
    return { ok: false, status: 401, error: tokenCheck.error };
  }

  const binding = await bindingsStore.getByDeviceId(deviceId);
  if (!binding) {
    return { ok: false, status: 401, error: "unknown_device" };
  }

  const deviceKeyHash = stableDeviceKeyHash(deviceKey);
  const payload = tokenCheck.payload;
  const bindingMatches =
    binding.deviceKeyHash === deviceKeyHash &&
    binding.machineFingerprint === machineFingerprint &&
    payload.sub === deviceId &&
    payload.dk === deviceKeyHash &&
    payload.fp === machineFingerprint;

  if (!bindingMatches) {
    return { ok: false, status: 403, error: "device_binding_mismatch" };
  }

  await bindingsStore.touchBinding(deviceId, new Date().toISOString());

  return { ok: true };
}

async function forwardToGroq(payload) {
  const groqKeys = getGroqKeys();
  if (!groqKeys.length) {
    return { status: 500, body: { error: { message: "missing_groq_key" } } };
  }

  const requestBody = {
    model: sanitizeString(payload.model, 120) || "llama-3.1-8b-instant",
    messages: Array.isArray(payload.messages) ? payload.messages : [],
    temperature: payload.temperature ?? 0.2,
    max_tokens: payload.max_tokens ?? 1024,
    stream: false,
  };

  const orderedKeys = orderedGroqKeys(groqKeys);
  const readyCount = orderedKeys.filter((keyConfig) => groqKeyCooldownRemaining(getGroqKeyState(keyConfig)) === 0).length;
  if (!readyCount) {
    const retryAfterSec = Math.min(
      ...orderedKeys
        .map((keyConfig) => groqKeyCooldownRemaining(getGroqKeyState(keyConfig)))
        .filter((value) => value > 0)
    );
    return {
      status: 503,
      body: {
        error: {
          message: "all_groq_keys_cooling_down",
          retry_after_sec: retryAfterSec || GROQ_KEY_COOLDOWN_SEC,
        },
      },
    };
  }

  for (let offset = 0; offset < orderedKeys.length; offset += 1) {
    const keyConfig = orderedKeys[offset];
    if (groqKeyCooldownRemaining(getGroqKeyState(keyConfig)) > 0) {
      continue;
    }
    const apiKey = keyConfig.value;
    try {
      const upstream = await fetch(`${GROQ_API_BASE_URL}/chat/completions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const responseText = await upstream.text();
      if (upstream.ok) {
        let parsed;
        try {
          parsed = JSON.parse(responseText);
        } catch (_error) {
          parsed = { raw: responseText };
        }
        markGroqKeySuccess(keyConfig);
        groqCursor = (keyConfig.index + 1) % groqKeys.length;
        return { status: upstream.status, body: parsed };
      }

      let parsedError;
      try {
        parsedError = JSON.parse(responseText);
      } catch (_error) {
        parsedError = { error: { message: responseText || "upstream_error" } };
      }
      const detail = String(parsedError?.error?.message || responseText || "upstream_error");
      let cooldownSec = 0;
      if (upstream.status === 429) {
        cooldownSec = GROQ_KEY_COOLDOWN_SEC;
      } else if (upstream.status === 401 || upstream.status === 403) {
        cooldownSec = GROQ_INVALID_KEY_COOLDOWN_SEC;
      }
      if (cooldownSec > 0) {
        markGroqKeyFailure(keyConfig, upstream.status, detail, cooldownSec);
      } else {
        markGroqKeyFailure(keyConfig, upstream.status, detail, 0);
      }
      if ([401, 403, 429].includes(upstream.status) && offset < orderedKeys.length - 1) {
        console.warn(`[Groq] ${keyConfig.label} failed with ${upstream.status}, cooldown=${cooldownSec}s`);
        continue;
      }
      groqCursor = (keyConfig.index + 1) % groqKeys.length;
      return { status: upstream.status, body: parsedError };
    } catch (error) {
      const detail = error && error.message ? error.message : "upstream_error";
      markGroqKeyFailure(keyConfig, 502, detail, GROQ_NETWORK_ERROR_COOLDOWN_SEC);
      if (offset < orderedKeys.length - 1) {
        console.warn(`[Groq] ${keyConfig.label} network error, cooldown=${GROQ_NETWORK_ERROR_COOLDOWN_SEC}s`);
        continue;
      }
      groqCursor = (keyConfig.index + 1) % groqKeys.length;
      return {
        status: 502,
        body: {
          error: {
            message: detail,
            type: "network_error",
          },
        },
      };
    }
  }

  return { status: 502, body: { error: { message: "upstream_error" } } };
}

function createServer() {
  return http.createServer(async (req, res) => {
  if (req.method === "OPTIONS") {
    res.writeHead(204, withCors({}));
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (req.method === "GET" && url.pathname === "/health") {
    const keyStates = listGroqKeyHealth();
    sendJson(res, 200, {
      ok: true,
      bindings_store: bindingsStoreInfo.type,
      bindings_target: bindingsStoreInfo.target,
      groq_api_base_url: GROQ_API_BASE_URL,
      groq_keys: keyStates.length,
      groq_ready_keys: keyStates.filter((item) => item.status === "ready").length,
      groq_cooling_keys: keyStates.filter((item) => item.status === "cooling_down").length,
      key_states: keyStates,
      time: new Date().toISOString(),
    });
    return;
  }

  if (!APP_TOKEN_SECRET) {
    sendJson(res, 500, { error: { message: "missing_app_token_secret" } });
    return;
  }

  if (req.method === "POST" && url.pathname === "/device/register") {
    try {
      const body = await readJsonBody(req);
      const result = await registerDevice(body);
      sendJson(res, result.status, result.body);
    } catch (_error) {
      sendJson(res, 400, { error: { message: "invalid_json" } });
    }
    return;
  }

  if (req.method === "POST" && url.pathname === "/openai/v1/chat/completions") {
    const authCheck = await verifyDeviceHeaders(req);
    if (!authCheck.ok) {
      sendJson(res, authCheck.status, { error: { message: authCheck.error } });
      return;
    }
    try {
      const payload = await readJsonBody(req);
      const upstream = await forwardToGroq(payload);
      sendJson(res, upstream.status, upstream.body);
    } catch (_error) {
      sendJson(res, 400, { error: { message: "invalid_json" } });
    }
    return;
  }

  sendJson(res, 404, { error: { message: "not_found" } });
});
}

async function startServer() {
  await bindingsStore.init();
  const server = createServer();
  server.listen(PORT, "0.0.0.0", () => {
    console.log(`EduPlay Northflank AI gateway listening on :${PORT}`);
    console.log(`Bindings store: ${bindingsStoreInfo.type}`);
    console.log(`Bindings target: ${bindingsStoreInfo.target}`);
    console.log(`Groq key count: ${getGroqKeys().length}`);
    console.log(`Groq API base URL: ${GROQ_API_BASE_URL}`);
  });
  return server;
}

if (require.main === module) {
  startServer().catch((error) => {
    console.error("Failed to start AI gateway", error);
    process.exit(1);
  });
}

module.exports = {
  createServer,
  registerDevice,
  verifyDeviceHeaders,
  startServer,
};
