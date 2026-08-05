const test = require("node:test");
const assert = require("node:assert/strict");
const { newDb } = require("pg-mem");

const {
  PostgresDeviceBindingsStore,
} = require("./device_bindings_store");

function createStore() {
  const db = newDb();
  const { Pool } = db.adapters.createPg();
  const pool = new Pool();
  const store = new PostgresDeviceBindingsStore({ pool });
  return { db, pool, store };
}

test("postgres store bootstraps schema and persists device bindings", async () => {
  const { pool, store } = createStore();
  await store.init();

  await store.upsertBinding({
    deviceId: "dev_alpha_1234567890",
    deviceKeyHash: "hash_alpha",
    machineFingerprint: "mfp_alpha_1234567890",
    platform: "Windows",
    appId: "eduplay-studio",
    createdAt: "2026-07-15T10:00:00.000Z",
    lastSeenAt: "2026-07-15T10:00:00.000Z",
  });

  const byDeviceId = await store.getByDeviceId("dev_alpha_1234567890");
  assert.equal(byDeviceId.deviceId, "dev_alpha_1234567890");
  assert.equal(byDeviceId.deviceKeyHash, "hash_alpha");
  assert.equal(byDeviceId.machineFingerprint, "mfp_alpha_1234567890");

  const byDeviceKeyHash = await store.getByDeviceKeyHash("hash_alpha");
  assert.equal(byDeviceKeyHash.deviceId, "dev_alpha_1234567890");

  await pool.end();
});

test("postgres store updates existing device binding last seen without changing created_at", async () => {
  const { pool, store } = createStore();
  await store.init();

  await store.upsertBinding({
    deviceId: "dev_alpha_1234567890",
    deviceKeyHash: "hash_alpha",
    machineFingerprint: "mfp_alpha_1234567890",
    platform: "Windows",
    appId: "eduplay-studio",
    createdAt: "2026-07-15T10:00:00.000Z",
    lastSeenAt: "2026-07-15T10:00:00.000Z",
  });

  await store.upsertBinding({
    deviceId: "dev_alpha_1234567890",
    deviceKeyHash: "hash_alpha",
    machineFingerprint: "mfp_alpha_1234567890",
    platform: "Windows 11",
    appId: "eduplay-studio",
    createdAt: "2026-07-15T10:00:00.000Z",
    lastSeenAt: "2026-07-15T12:30:00.000Z",
  });

  const binding = await store.getByDeviceId("dev_alpha_1234567890");
  assert.equal(binding.createdAt, "2026-07-15T10:00:00.000Z");
  assert.equal(binding.lastSeenAt, "2026-07-15T12:30:00.000Z");
  assert.equal(binding.platform, "Windows 11");

  await pool.end();
});
