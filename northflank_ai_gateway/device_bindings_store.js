const fs = require("node:fs");
const path = require("node:path");
const { Pool } = require("pg");

function ensureDataDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function readJsonFile(filePath) {
  try {
    if (!fs.existsSync(filePath)) {
      return {};
    }
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (_error) {
    return {};
  }
}

function writeJsonFileAtomic(filePath, payload) {
  const tmpFile = `${filePath}.tmp`;
  fs.writeFileSync(tmpFile, JSON.stringify(payload, null, 2), "utf8");
  fs.renameSync(tmpFile, filePath);
}

function toBindingRecord(row) {
  if (!row) {
    return null;
  }
  return {
    deviceId: row.device_id,
    deviceKeyHash: row.device_key_hash,
    machineFingerprint: row.machine_fingerprint,
    platform: row.platform,
    appId: row.app_id,
    createdAt: toIsoString(row.created_at),
    lastSeenAt: toIsoString(row.last_seen_at),
  };
}

function toIsoString(value) {
  if (!value) {
    return "";
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toISOString();
  }
  return String(value);
}

class JsonFileDeviceBindingsStore {
  constructor(options = {}) {
    this.dataDir = path.resolve(options.dataDir || path.join(__dirname, "data"));
    this.bindingsFile = path.resolve(options.bindingsFile || path.join(this.dataDir, "device_bindings.json"));
  }

  async init() {
    ensureDataDir(this.dataDir);
  }

  async getByDeviceId(deviceId) {
    const bindings = readJsonFile(this.bindingsFile);
    return bindings[deviceId] || null;
  }

  async getByDeviceKeyHash(deviceKeyHash) {
    const bindings = readJsonFile(this.bindingsFile);
    for (const binding of Object.values(bindings)) {
      if (binding && binding.deviceKeyHash === deviceKeyHash) {
        return binding;
      }
    }
    return null;
  }

  async upsertBinding(binding) {
    ensureDataDir(this.dataDir);
    const bindings = readJsonFile(this.bindingsFile);
    const existing = bindings[binding.deviceId] || null;
    bindings[binding.deviceId] = {
      ...binding,
      createdAt: existing && existing.createdAt ? existing.createdAt : binding.createdAt,
    };
    writeJsonFileAtomic(this.bindingsFile, bindings);
    return bindings[binding.deviceId];
  }

  async touchBinding(deviceId, lastSeenAt) {
    ensureDataDir(this.dataDir);
    const bindings = readJsonFile(this.bindingsFile);
    if (!bindings[deviceId]) {
      return null;
    }
    bindings[deviceId] = {
      ...bindings[deviceId],
      lastSeenAt,
    };
    writeJsonFileAtomic(this.bindingsFile, bindings);
    return bindings[deviceId];
  }

  describe() {
    return {
      type: "json",
      target: this.bindingsFile,
    };
  }

  async close() {}
}

class PostgresDeviceBindingsStore {
  constructor(options = {}) {
    this.tableName = sanitizeSqlIdentifier(options.tableName || "device_bindings");
    this.pool = options.pool || new Pool({
      connectionString: String(options.connectionString || "").trim(),
      ssl: options.ssl ?? resolveSslOption(String(options.connectionString || "").trim()),
    });
    this.ownsPool = !options.pool;
  }

  async init() {
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS ${this.tableName} (
        device_id TEXT PRIMARY KEY,
        device_key_hash TEXT NOT NULL UNIQUE,
        machine_fingerprint TEXT NOT NULL,
        platform TEXT NOT NULL DEFAULT '',
        app_id TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMPTZ NOT NULL,
        last_seen_at TIMESTAMPTZ NOT NULL
      )
    `);
    await this.pool.query(`
      CREATE INDEX IF NOT EXISTS ${this.tableName}_machine_fingerprint_idx
      ON ${this.tableName} (machine_fingerprint)
    `);
  }

  async getByDeviceId(deviceId) {
    const result = await this.pool.query(
      `
        SELECT
          device_id,
          device_key_hash,
          machine_fingerprint,
          platform,
          app_id,
          created_at,
          last_seen_at
        FROM ${this.tableName}
        WHERE device_id = $1
      `,
      [deviceId]
    );
    return toBindingRecord(result.rows[0]);
  }

  async getByDeviceKeyHash(deviceKeyHash) {
    const result = await this.pool.query(
      `
        SELECT
          device_id,
          device_key_hash,
          machine_fingerprint,
          platform,
          app_id,
          created_at,
          last_seen_at
        FROM ${this.tableName}
        WHERE device_key_hash = $1
      `,
      [deviceKeyHash]
    );
    return toBindingRecord(result.rows[0]);
  }

  async upsertBinding(binding) {
    await this.pool.query(
      `
        INSERT INTO ${this.tableName} (
          device_id,
          device_key_hash,
          machine_fingerprint,
          platform,
          app_id,
          created_at,
          last_seen_at
        ) VALUES ($1, $2, $3, $4, $5, $6::timestamptz, $7::timestamptz)
        ON CONFLICT (device_id) DO UPDATE SET
          device_key_hash = EXCLUDED.device_key_hash,
          machine_fingerprint = EXCLUDED.machine_fingerprint,
          platform = EXCLUDED.platform,
          app_id = EXCLUDED.app_id,
          last_seen_at = EXCLUDED.last_seen_at
      `,
      [
        binding.deviceId,
        binding.deviceKeyHash,
        binding.machineFingerprint,
        binding.platform || "",
        binding.appId || "",
        binding.createdAt,
        binding.lastSeenAt,
      ]
    );
    return this.getByDeviceId(binding.deviceId);
  }

  async touchBinding(deviceId, lastSeenAt) {
    const result = await this.pool.query(
      `
        UPDATE ${this.tableName}
        SET last_seen_at = $2::timestamptz
        WHERE device_id = $1
        RETURNING
          device_id,
          device_key_hash,
          machine_fingerprint,
          platform,
          app_id,
          created_at,
          last_seen_at
      `,
      [deviceId, lastSeenAt]
    );
    return toBindingRecord(result.rows[0]);
  }

  describe() {
    return {
      type: "postgres",
      target: this.tableName,
    };
  }

  async close() {
    if (this.ownsPool) {
      await this.pool.end();
    }
  }
}

function resolveSslOption(connectionString) {
  if (!connectionString) {
    return false;
  }
  return { rejectUnauthorized: false };
}

function createDeviceBindingsStoreFromEnv(env = process.env, options = {}) {
  const dataDir = options.dataDir || env.DATA_DIR || path.join(__dirname, "data");
  const bindingsFile = options.bindingsFile || path.join(dataDir, "device_bindings.json");
  const tableName = sanitizeSqlIdentifier(env.DEVICE_BINDINGS_TABLE || "device_bindings");
  const connectionString = String(
    env.SUPABASE_DB_URL || env.DATABASE_URL || env.POSTGRES_URL || ""
  ).trim();
  const mode = String(env.DEVICE_BINDINGS_MODE || "auto").trim().toLowerCase();

  if (mode === "postgres" && !connectionString) {
    throw new Error("DEVICE_BINDINGS_MODE=postgres requires DATABASE_URL or SUPABASE_DB_URL");
  }

  if (mode === "postgres" || (mode === "auto" && connectionString)) {
    return new PostgresDeviceBindingsStore({
      connectionString,
      tableName,
    });
  }

  return new JsonFileDeviceBindingsStore({
    dataDir,
    bindingsFile,
  });
}

function sanitizeSqlIdentifier(value) {
  const input = String(value || "").trim();
  if (!input) {
    return "device_bindings";
  }
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(input)) {
    throw new Error(`Invalid SQL identifier: ${input}`);
  }
  return input;
}

module.exports = {
  JsonFileDeviceBindingsStore,
  PostgresDeviceBindingsStore,
  createDeviceBindingsStoreFromEnv,
};
