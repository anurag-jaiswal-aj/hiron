import * as crypto from "crypto";

export function generateQStashSignature(body: string, secret: string, url: string = ""): string {
  const headerObj = { alg: "HS256", typ: "JWT" };
  const header = Buffer.from(JSON.stringify(headerObj)).toString("base64url");

  const bodyHash = crypto.createHash("sha256").update(body).digest("base64url");

  const now = Math.floor(Date.now() / 1000);
  const payloadObj = {
    iss: "Upstash",
    sub: url,
    exp: now + 300,
    nbf: now - 300,
    iat: now,
    jti: crypto.randomUUID(),
    body: bodyHash,
  };
  const payload = Buffer.from(JSON.stringify(payloadObj)).toString("base64url");

  const signature = crypto
    .createHmac("sha256", secret)
    .update(`${header}.${payload}`)
    .digest("base64url");

  return `${header}.${payload}.${signature}`;
}
