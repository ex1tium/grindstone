// Semantic hashing, steps 4 to 6 of SPEC-01 (ADR-44), the twin of
// grindstone.contracts.hashing. It takes an already projected JSON value: the
// TypeScript side has no Pydantic projection (steps 1 to 3).
//
// 4. Normalise every string, keys included, to NFC and line endings to LF;
//    refuse keys that collide after normalisation, and any float, unsafe
//    integer or non-JSON value, with `hash_input_invalid`.
// 5. Canonicalise with RFC 8785.
// 6. Hash the UTF-8 bytes with SHA-256, written `sha256:<hex>`.
//
// The golden vectors in grindstone/contracts/golden/hash-vectors.json bind both.
import { createHash } from "node:crypto";
import canonicalize from "canonicalize";
import type { ErrorEnvelope } from "./index.ts";

/** A JSON value after normalisation: the only input canonicalisation sees. */
export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

/** A semantic hash: `sha256:` and 64 lowercase hex digits. */
export type SemanticHash = `sha256:${string}`;

/** Content that cannot be hashed the same way everywhere, with code `hash_input_invalid`. */
export class HashInputError extends Error {
  readonly envelope: ErrorEnvelope;

  constructor(message: string, pointer: string) {
    super(`${message} at ${pointer || "/"}`);
    this.name = "HashInputError";
    this.envelope = {
      code: "hash_input_invalid",
      error_class: "validation",
      message,
      detail: { pointer },
      retryable: false,
      schema_version: 1,
    };
  }
}

/** Step 4: NFC and LF for every string and key; refuse what cannot hash alike everywhere. */
export function normalise(value: unknown, pointer = ""): Json {
  if (typeof value === "string") {
    return text(value, pointer);
  }
  if (value === null || typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    // JavaScript has one number type, so `1.0` arrives as the integer 1 and
    // hashes as 1; only a value with a fraction, or NaN or Infinity, is a float.
    if (!Number.isInteger(value)) {
      throw new HashInputError(`a float cannot be hashed: ${value}`, pointer);
    }
    if (!Number.isSafeInteger(value)) {
      throw new HashInputError(`integer ${value} is outside ±(2^53 - 1)`, pointer);
    }
    // -0 is not an integer anywhere else; it hashes as 0.
    return value === 0 ? 0 : value;
  }
  if (Array.isArray(value)) {
    const items: unknown[] = value;
    const out: Json[] = [];
    // An index loop, not map(): a hole in a sparse array is refused, not skipped.
    for (let i = 0; i < items.length; i++) {
      out.push(normalise(items[i], `${pointer}/${i}`));
    }
    return out;
  }
  if (typeof value === "object" && isPlainObject(value)) {
    if (Object.getOwnPropertySymbols(value).length > 0) {
      throw new HashInputError("an object key is a symbol, not a string", pointer);
    }
    // A null prototype, so a `__proto__` key stays an ordinary key.
    const out: { [key: string]: Json } = Object.create(null);
    for (const [key, item] of Object.entries(value)) {
      const norm = text(key, pointer);
      if (Object.hasOwn(out, norm)) {
        throw new HashInputError(
          `keys collide after normalisation: ${JSON.stringify(norm)}`,
          pointer,
        );
      }
      out[norm] = normalise(item, `${pointer}/${escapePointer(norm)}`);
    }
    return out;
  }
  throw new HashInputError(`${describe(value)} is not a JSON value`, pointer);
}

/** Steps 4 and 5: the RFC 8785 canonical bytes of an already projected JSON value. */
export function canonicalBytes(value: unknown): Uint8Array {
  const json = canonicalize(normalise(value));
  if (json === undefined) {
    // Unreachable: normalise returns only JSON values, which always serialise.
    throw new HashInputError("value has no JSON form", "");
  }
  return new TextEncoder().encode(json);
}

/** Step 6: `sha256:` and the lowercase hex digest. */
export function hashBytes(data: Uint8Array): SemanticHash {
  return `sha256:${createHash("sha256").update(data).digest("hex")}`;
}

/** The semantic hash of an already projected JSON value: what freshness compares (ADR-11). */
export function semanticHash(value: unknown): SemanticHash {
  return hashBytes(canonicalBytes(value));
}

function text(value: string, pointer: string): string {
  // A lone surrogate has no UTF-8 form, so no implementation can hash it alike.
  if (!value.isWellFormed()) {
    throw new HashInputError("a string contains a lone surrogate", pointer);
  }
  return value.normalize("NFC").replaceAll("\r\n", "\n").replaceAll("\r", "\n");
}

function isPlainObject(value: object): boolean {
  const proto: unknown = Object.getPrototypeOf(value);
  return proto === Object.prototype || proto === null;
}

function escapePointer(key: string): string {
  return key.replaceAll("~", "~0").replaceAll("/", "~1");
}

function describe(value: unknown): string {
  if (typeof value === "bigint") {
    return `bigint ${value}`;
  }
  if (typeof value === "object" && value !== null) {
    return value.constructor?.name ?? "object";
  }
  return typeof value;
}
