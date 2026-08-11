import { test, expect } from "@playwright/test";
import { JSDOM } from "jsdom";
import createDOMPurify from "dompurify";
const window = new JSDOM("").window;
const DOMPurify = createDOMPurify(window as unknown as Window);

test.describe("XSS Prevention via DOMPurify", () => {
  test("dangerouslySetInnerHTML payloads are sanitized correctly", async () => {
    const payloads = [
      {
        original: "<script>alert(1)</script>",
        expected: ""
      },
      {
        original: "<img src=x onerror=alert(1)>",
        expected: "<img src=\"x\">"
      },
      {
        original: "<svg onload=alert(1)>",
        expected: "<svg></svg>"
      },
      {
        original: "<a href=\"javascript:alert(1)\">click</a> <b>safe</b>",
        expected: "<a>click</a> <b>safe</b>"
      }
    ];

    for (const { original, expected } of payloads) {
      const sanitized = DOMPurify.sanitize(original);
      expect(sanitized).toBe(expected);
      expect(sanitized).not.toContain("alert(1)");
    }
  });
});
