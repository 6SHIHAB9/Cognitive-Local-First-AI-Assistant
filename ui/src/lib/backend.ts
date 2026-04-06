const BACKEND_URL = "http://192.168.20.7:8000";

async function post(endpoint: string, body: any) {
  const res = await fetch(`${BACKEND_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export function syncVault() {
  return post("/sync", {});
}

export async function sendMessageStream(
  message: string,
  onToken: (token: string) => void,
  onDone: (metadata: any, syncInfo: any) => void
) {
  const res = await fetch(`${BACKEND_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: message }),
  });

  // Handle non-streaming responses (refusals happen before streaming)
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const data = await res.json();
    onToken(data.answer ?? "No response.");
    onDone(null, data.sync_performed ?? null);
    return;
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value);
    const lines = text.split("\n").filter((l) => l.startsWith("data: "));

    for (const line of lines) {
      try {
        const data = JSON.parse(line.replace("data: ", ""));
        if (data.token) {
          onToken(data.token);
        }
        if (data.done) {
          onDone(data.metadata ?? null, data.sync_info ?? null);
        }
      } catch {
        // ignore malformed chunks
      }
    }
  }
}