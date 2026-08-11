import { test, expect } from "@playwright/test";
import { JSDOM } from "jsdom";
import createDOMPurify from "dompurify";
const window = new JSDOM("").window;
const DOMPurify = createDOMPurify(window as unknown as Window);

test("DOMPurify sanitizes malicious payloads", () => {
  const maliciousPayloads = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "<a href=\"javascript:alert(1)\">click</a> <b>safe</b>"
  ];

  for (const payload of maliciousPayloads) {
    const sanitized = DOMPurify.sanitize(payload);
    expect(sanitized).not.toContain("alert(1)");
  }
});
