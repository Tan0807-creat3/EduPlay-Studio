const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const http = require("node:http");

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForHealth(baseUrl, attempts = 40) {
  for (let index = 0; index < attempts; index += 1) {
    try {
      const resp = await fetch(`${baseUrl}/health`);
      if (resp.ok) {
        return;
      }
    } catch (_error) {
      // Server may still be starting.
    }
    await wait(150);
  }
  throw new Error("gateway did not become healthy in time");
}

async function registerDevice(baseUrl) {
  const registerBody = {
    device_id: "dev_alpha_1234567890",
    device_key: "dkey_same_device_key_1234567890",
    machine_fingerprint: "mfp_machine_alpha_1234567890",
    platform: "Windows",
    app_id: "eduplay-studio",
  };
  const resp = await fetch(`${baseUrl}/device/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(registerBody),
  });
  assert.equal(resp.status, 200);
  const payload = await resp.json();
  return {
    accessToken: payload.access_token,
    deviceId: registerBody.device_id,
    deviceKey: registerBody.device_key,
    machineFingerprint: registerBody.machine_fingerprint,
  };
}

test("rejects reusing one device key across another device id", async () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "eduplay-nf-gateway-"));
  const port = 39231;
  const child = spawn(process.execPath, ["server.js"], {
    cwd: __dirname,
    env: {
      ...process.env,
      GROQ_API_KEYS: "",
      GROQ_API_KEY: "gsk_test_unused",
      GROQ_KEY_1: "",
      GROQ_KEY_2: "",
      GROQ_KEY_3: "",
      PORT: String(port),
      DATA_DIR: tempDir,
      APP_TOKEN_SECRET: "test_app_secret_123",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  try {
    await waitForHealth(`http://127.0.0.1:${port}`);

    const registerBody = {
      device_key: "dkey_same_device_key_1234567890",
      machine_fingerprint: "mfp_machine_alpha_1234567890",
      platform: "Windows",
      app_id: "eduplay-studio",
    };

    const firstResp = await fetch(`http://127.0.0.1:${port}/device/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...registerBody,
        device_id: "dev_alpha_1234567890",
      }),
    });
    assert.equal(firstResp.status, 200);

    const secondResp = await fetch(`http://127.0.0.1:${port}/device/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...registerBody,
        device_id: "dev_beta_1234567890",
      }),
    });
    assert.equal(secondResp.status, 403);

    const secondPayload = await secondResp.json();
    assert.equal(secondPayload?.error?.message, "device_key_already_bound");
  } finally {
    child.kill("SIGTERM");
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});

test("puts rate-limited key on cooldown and reports key health", async () => {
  const upstreamRequests = [];
  const upstreamPort = 39232;
  const upstreamServer = http.createServer(async (req, res) => {
    let raw = "";
    for await (const chunk of req) {
      raw += chunk.toString("utf8");
    }
    const auth = String(req.headers.authorization || "");
    upstreamRequests.push(auth);
    if (auth === "Bearer gsk_test_key_1") {
      res.writeHead(429, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: { message: "rate_limit_exceeded" } }));
      return;
    }
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ choices: [{ message: { content: `ok:${auth}` } }] }));
  });
  await new Promise((resolve) => upstreamServer.listen(upstreamPort, "127.0.0.1", resolve));

  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "eduplay-nf-gateway-"));
  const port = 39233;
  const child = spawn(process.execPath, ["server.js"], {
    cwd: __dirname,
    env: {
      ...process.env,
      GROQ_API_KEYS: "",
      GROQ_API_KEY: "",
      PORT: String(port),
      DATA_DIR: tempDir,
      APP_TOKEN_SECRET: "test_app_secret_456",
      GROQ_KEY_1: "gsk_test_key_1",
      GROQ_KEY_2: "gsk_test_key_2",
      GROQ_KEY_3: "gsk_test_key_3",
      GROQ_KEY_COOLDOWN_SEC: "120",
      GROQ_API_BASE_URL: `http://127.0.0.1:${upstreamPort}/openai/v1`,
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  try {
    const baseUrl = `http://127.0.0.1:${port}`;
    await waitForHealth(baseUrl);
    const auth = await registerDevice(baseUrl);

    const headers = {
      Authorization: `Bearer ${auth.accessToken}`,
      "Content-Type": "application/json",
      "X-Device-Id": auth.deviceId,
      "X-Device-Key": auth.deviceKey,
      "X-Machine-Fingerprint": auth.machineFingerprint,
    };

    const firstChat = await fetch(`${baseUrl}/openai/v1/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: "llama-3.1-8b-instant",
        messages: [{ role: "user", content: "hello" }],
      }),
    });
    assert.equal(firstChat.status, 200);
    const firstPayload = await firstChat.json();
    assert.equal(firstPayload?.choices?.[0]?.message?.content, "ok:Bearer gsk_test_key_2");

    const secondChat = await fetch(`${baseUrl}/openai/v1/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: "llama-3.1-8b-instant",
        messages: [{ role: "user", content: "hello again" }],
      }),
    });
    assert.equal(secondChat.status, 200);
    const secondPayload = await secondChat.json();
    assert.equal(secondPayload?.choices?.[0]?.message?.content, "ok:Bearer gsk_test_key_3");

    assert.deepEqual(upstreamRequests, [
      "Bearer gsk_test_key_1",
      "Bearer gsk_test_key_2",
      "Bearer gsk_test_key_3",
    ]);

    const healthResp = await fetch(`${baseUrl}/health`);
    assert.equal(healthResp.status, 200);
    const health = await healthResp.json();
    assert.equal(health.groq_keys, 3);
    assert.equal(Array.isArray(health.key_states), true);
    assert.equal(health.key_states.length, 3);
    assert.equal(health.key_states[0]?.status, "cooling_down");
    assert.equal(health.key_states[0]?.last_status_code, 429);
    assert.equal(health.key_states[1]?.status, "ready");
  } finally {
    child.kill("SIGTERM");
    upstreamServer.close();
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});
