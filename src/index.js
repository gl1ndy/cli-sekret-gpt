const DEFAULT_MODEL = "openai/gpt-oss-120b";
const MAX_PROMPT_LENGTH = 20_000;
const MAX_SYSTEM_LENGTH = 5_000;
const MAX_OUTPUT_TOKENS = 4_096;

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return json({
        error: "method_not_allowed",
        message: "Используйте POST-запрос.",
      }, 405, { Allow: "POST" });
    }

    if (!env.GROQ_API_KEY || !env.API_PASSWORD) {
      return json({
        error: "server_misconfigured",
        message: "На сервере не настроены GROQ_API_KEY или API_PASSWORD.",
      }, 500);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({
        error: "invalid_json",
        message: "Тело запроса должно быть корректным JSON.",
      }, 400);
    }

    const suppliedPassword = getPassword(request, body);
    if (!suppliedPassword || !(await safeEqual(suppliedPassword, env.API_PASSWORD))) {
      return json({
        error: "unauthorized",
        message: "Неверный пароль.",
      }, 401);
    }

    if (typeof body.prompt !== "string" || body.prompt.trim() === "") {
      return json({
        error: "invalid_prompt",
        message: "Поле prompt обязательно и должно быть непустой строкой.",
      }, 400);
    }

    if (body.prompt.length > MAX_PROMPT_LENGTH) {
      return json({
        error: "prompt_too_long",
        message: `Максимальная длина prompt — ${MAX_PROMPT_LENGTH} символов.`,
      }, 413);
    }

    const messages = [];
    if (typeof body.system === "string" && body.system.trim() !== "") {
      if (body.system.length > MAX_SYSTEM_LENGTH) {
        return json({
          error: "system_too_long",
          message: `Максимальная длина system — ${MAX_SYSTEM_LENGTH} символов.`,
        }, 413);
      }
      messages.push({ role: "system", content: body.system });
    }
    messages.push({ role: "user", content: body.prompt });

    const maxCompletionTokens = clampInteger(
      body.max_tokens,
      1,
      MAX_OUTPUT_TOKENS,
      1_024,
    );
    const temperature = clampNumber(body.temperature, 0, 2, 0.7);

    let groqResponse;
    try {
      groqResponse = await fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GROQ_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: env.GROQ_MODEL || DEFAULT_MODEL,
          messages,
          temperature,
          max_completion_tokens: maxCompletionTokens,
          stream: false,
        }),
      });
    } catch {
      return json({
        error: "upstream_unreachable",
        message: "Не удалось связаться с Groq.",
      }, 502);
    }

    const groqData = await groqResponse.json().catch(() => null);
    if (!groqResponse.ok) {
      return json({
        error: "groq_error",
        message: "Groq вернул ошибку.",
        status: groqResponse.status,
        details: groqData?.error?.message || undefined,
      }, 502);
    }

    const answer = groqData?.choices?.[0]?.message?.content;
    if (typeof answer !== "string") {
      return json({
        error: "invalid_groq_response",
        message: "Groq вернул ответ неожиданного формата.",
      }, 502);
    }

    return json({
      answer,
      model: groqData.model || env.GROQ_MODEL || DEFAULT_MODEL,
      usage: groqData.usage || null,
    });
  },
};

function getPassword(request, body) {
  const authorization = request.headers.get("Authorization") || "";
  if (authorization.startsWith("Bearer ")) {
    return authorization.slice("Bearer ".length).trim();
  }

  return typeof body?.password === "string" ? body.password : "";
}

async function safeEqual(left, right) {
  const encoder = new TextEncoder();
  const [leftHash, rightHash] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(left)),
    crypto.subtle.digest("SHA-256", encoder.encode(right)),
  ]);
  const leftBytes = new Uint8Array(leftHash);
  const rightBytes = new Uint8Array(rightHash);
  let difference = 0;
  for (let index = 0; index < leftBytes.length; index += 1) {
    difference |= leftBytes[index] ^ rightBytes[index];
  }
  return difference === 0;
}

function clampInteger(value, min, max, fallback) {
  if (value === undefined || value === null || value === "") return fallback;
  const number = Number(value);
  if (!Number.isInteger(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function clampNumber(value, min, max, fallback) {
  if (value === undefined || value === null || value === "") return fallback;
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...extraHeaders,
    },
  });
}
