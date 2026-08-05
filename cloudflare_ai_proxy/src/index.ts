type Env = {
  PROXY_TOKEN?: string
  TOKEN_SECRET?: string
  GROQ_KEY_1?: string
  GROQ_KEY_2?: string
  GROQ_KEY_3?: string
}

let groqRrCursor = 0

function getGroqKeys(env: Env): string[] {
  return [env.GROQ_KEY_1, env.GROQ_KEY_2, env.GROQ_KEY_3].filter((x) => !!x && String(x).trim().length > 0) as string[]
}

function withCors(resp: Response): Response {
  const h = new Headers(resp.headers)
  h.set("Access-Control-Allow-Origin", "*")
  h.set("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
  h.set("Access-Control-Allow-Headers", "authorization,content-type,x-device-id")
  return new Response(resp.body, { status: resp.status, headers: h })
}

function jsonResponse(data: any, status: number = 200): Response {
  return withCors(new Response(JSON.stringify(data), { 
    status, 
    headers: { "content-type": "application/json" } 
  }))
}

function base64Url(bytes: ArrayBuffer): string {
  const arr = new Uint8Array(bytes)
  let s = ""
  for (let i = 0; i < arr.length; i++) s += String.fromCharCode(arr[i])
  const b64 = btoa(s)
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "")
}

async function hmacToken(secret: string, deviceId: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  )
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(deviceId))
  return base64Url(sig)
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") {
      return withCors(new Response(null, { status: 204 }))
    }

    const url = new URL(request.url)
    
    // Register endpoint
    if (url.pathname === "/register") {
      if (request.method !== "POST") {
        return withCors(new Response("method_not_allowed", { status: 405 }))
      }
      const secret = env.TOKEN_SECRET || ""
      if (!secret) {
        return withCors(new Response("missing_token_secret", { status: 500 }))
      }
      let body: any = null
      try {
        body = await request.json()
      } catch (_e) {
        return withCors(new Response("invalid_json", { status: 400 }))
      }
      const deviceId = String(body?.device_id || "").trim()
      if (!deviceId || deviceId.length < 8 || deviceId.length > 128) {
        return withCors(new Response("bad_device_id", { status: 400 }))
      }
      const token = await hmacToken(secret, deviceId)
      return jsonResponse({ token })
    }

    // Auth verification
    const auth = request.headers.get("authorization") || ""
    const master = env.PROXY_TOKEN || ""
    const secret = env.TOKEN_SECRET || ""
    
    let authOk = false
    if (secret) {
      const deviceId = request.headers.get("x-device-id") || ""
      if (deviceId) {
        const expected = await hmacToken(secret, deviceId)
        if (auth === `Bearer ${expected}`) {
          authOk = true
        }
      }
      // Fallback to master token
      if (!authOk && master && auth === `Bearer ${master}`) {
        authOk = true
      }
    } else if (master && auth === `Bearer ${master}`) {
      authOk = true
    }
    
    if (!authOk) {
      return withCors(new Response("unauthorized", { status: 401 }))
    }

    // Only handle chat completions
    if (url.pathname !== "/openai/v1/chat/completions") {
      return withCors(new Response("not_found", { status: 404 }))
    }

    const keys = getGroqKeys(env)
    if (!keys.length) {
      return jsonResponse({ error: { message: "missing_groq_key" } }, 500)
    }

    // Parse request body
    let reqBody: any = null
    try {
      reqBody = await request.json()
    } catch (_e) {
      return jsonResponse({ error: { message: "invalid_json" } }, 400)
    }

    // Round-robin through keys
    const start = ((groqRrCursor % keys.length) + keys.length) % keys.length
    groqRrCursor = (start + 1) % keys.length

    let lastResp: Response | null = null
    for (let i = 0; i < keys.length; i++) {
      const apiKey = keys[(start + i) % keys.length]
      
      try {
        console.log("[PROXY] Calling Groq API with key index:", (start + i) % keys.length)
        
        // Call Groq API directly with clean request
        const groqResp = await fetch("https://api.groq.com/openai/v1/chat/completions", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${apiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: reqBody.model || "llama-3.1-8b-instant",
            messages: reqBody.messages || [],
            temperature: reqBody.temperature ?? 0.2,
            max_tokens: reqBody.max_tokens ?? 1024,
            stream: false,
          }),
        })

        lastResp = groqResp
        
        console.log("[PROXY] Groq response status:", groqResp.status)
        
        // Success - return response
        if (groqResp.ok) {
          return withCors(groqResp)
        }
        
        // Log error for debugging
        const errorText = await groqResp.text()
        console.error("[PROXY] Groq error:", {
          status: groqResp.status,
          body: errorText.substring(0, 500)
        })
        
        // Retry on auth/rate limit with next key
        if (groqResp.status === 401 || groqResp.status === 403 || groqResp.status === 429) {
          if (i < keys.length - 1) {
            console.log("[PROXY] Retrying with next key...")
            continue
          }
        }
        
        // Return error response
        return withCors(new Response(errorText, { 
          status: groqResp.status,
          headers: { "content-type": "application/json" }
        }))
        
      } catch (error: any) {
        console.error("[PROXY] Fetch error:", error.message || String(error))
        
        // Try next key on network errors
        if (i < keys.length - 1) {
          continue
        }
        
        return jsonResponse({ 
          error: { 
            message: error.message || "upstream_error",
            type: "network_error"
          } 
        }, 502)
      }
    }

    return withCors(lastResp || new Response("upstream_error", { status: 502 }))
  },
}
