// AC-0108-2: TypeScript reproduces every golden vector's canonical bytes and
// hash, and refuses every refusal vector with its code (SPEC-01, REQ-0108).
// The golden file is read from its Python home, never copied.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import canonicalize from "canonicalize";
import { canonicalBytes, HashInputError, normalise, semanticHash } from "../src/hashing.ts";

interface Vector {
  name: string;
  input: unknown;
  canonical: string;
  hash: string;
}

interface Refusal {
  name: string;
  input: unknown;
  code: string;
  substitute?: { pointer: string; kind: string };
}

interface Golden {
  vectors: Vector[];
  refusals: Refusal[];
}

const goldenUrl = new URL(
  "../../grindstone/src/grindstone/contracts/golden/hash-vectors.json",
  import.meta.url,
);
const golden = JSON.parse(readFileSync(goldenUrl, "utf8")) as Golden;

// TypeScript's non-JSON values, each placed at a `substitute` pointer in turn.
const nonJson: ReadonlyArray<[string, unknown]> = [
  ["undefined", undefined],
  ["a function", () => 1],
  ["a symbol", Symbol("x")],
  ["a bigint", 1n],
  ["NaN", Number.NaN],
  ["Infinity", Number.POSITIVE_INFINITY],
  ["a Date", new Date(0)],
  ["a Map", new Map()],
];

function decode(bytes: Uint8Array): string {
  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}

function refuses(input: unknown, code: string, pointer?: string): void {
  assert.throws(
    () => semanticHash(input),
    (err: unknown) => {
      assert.ok(err instanceof HashInputError);
      assert.equal(err.envelope.code, code);
      assert.equal(err.envelope.error_class, "validation");
      assert.equal(err.envelope.retryable, false);
      if (pointer !== undefined) {
        assert.equal(err.envelope.detail.pointer, pointer);
      }
      return true;
    },
  );
}

function place(input: unknown, pointer: string, value: unknown): unknown {
  const copy = structuredClone(input) as Record<string, unknown>;
  const parts = pointer.split("/").slice(1);
  let target: Record<string, unknown> = copy;
  for (const part of parts.slice(0, -1)) {
    target = target[part] as Record<string, unknown>;
  }
  const last = parts.at(-1);
  assert.ok(last !== undefined);
  target[last] = value;
  return copy;
}

test("the golden file has vectors and refusals", () => {
  assert.ok(golden.vectors.length > 0);
  assert.ok(golden.refusals.length > 0);
});

for (const v of golden.vectors) {
  test(`golden vector: ${v.name}`, () => {
    assert.equal(decode(canonicalBytes(v.input)), v.canonical);
    assert.equal(semanticHash(v.input), v.hash);
  });
}

for (const r of golden.refusals) {
  if (r.substitute === undefined) {
    test(`refusal vector: ${r.name}`, () => {
      refuses(r.input, r.code);
    });
    continue;
  }
  const { pointer } = r.substitute;
  for (const [label, value] of nonJson) {
    test(`refusal vector: ${r.name} (${label} at ${pointer})`, () => {
      refuses(place(r.input, pointer, value), r.code, pointer);
    });
  }
}

// OQ-0101: rfc8785 0.1.4 writes these bytes for U+0000 to U+001F, then U+007F,
// U+2028, U+2029, "/", '"' and "\" (checked with `rfc8785.dumps`). The golden
// vector runs after LF normalisation, so it cannot show how CR itself escapes;
// this compares the canonicalisers directly, without normalisation.
test("canonicalize escapes every control character as rfc8785 does (OQ-0101)", () => {
  let raw = "";
  for (let c = 0; c <= 0x1f; c++) {
    raw += String.fromCharCode(c);
  }
  raw += '\u007f  /"\\';
  const expected =
    '"\\u0000\\u0001\\u0002\\u0003\\u0004\\u0005\\u0006\\u0007\\b\\t\\n\\u000b\\f\\r' +
    "\\u000e\\u000f\\u0010\\u0011\\u0012\\u0013\\u0014\\u0015\\u0016\\u0017\\u0018" +
    '\\u0019\\u001a\\u001b\\u001c\\u001d\\u001e\\u001f\u007f  /\\"\\\\"';
  assert.equal(canonicalize(raw), expected);
});

test("a nested refusal reports its JSON pointer, escaped", () => {
  refuses({ "a/b": [{ "~": 1.5 }] }, "hash_input_invalid", "/a~1b/0/~0");
});

test("a lone surrogate is refused", () => {
  refuses({ x: "\ud800" }, "hash_input_invalid", "/x");
  refuses({ "\udc00": 1 }, "hash_input_invalid", "");
});

test("a hole in a sparse array is refused", () => {
  // biome-ignore lint/suspicious/noSparseArray: the hole is the point.
  refuses({ x: [1, , 3] }, "hash_input_invalid", "/x/1");
});

test("a symbol key and a class instance are refused", () => {
  refuses({ [Symbol("k")]: 1 }, "hash_input_invalid", "");
  refuses({ x: new (class Point {})() }, "hash_input_invalid", "/x");
});

test("a __proto__ key is an ordinary key", () => {
  const input = JSON.parse('{"__proto__":{"a":1},"b":2}') as unknown;
  assert.equal(decode(canonicalBytes(input)), '{"__proto__":{"a":1},"b":2}');
});

test("negative zero hashes as zero", () => {
  assert.deepEqual(normalise(-0), 0);
  assert.equal(semanticHash({ x: -0 }), semanticHash({ x: 0 }));
});
