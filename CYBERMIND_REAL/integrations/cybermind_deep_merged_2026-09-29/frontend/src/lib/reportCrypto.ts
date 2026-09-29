const FORMAT = "CYBERMIND_Encrypted_Incident_Brief";
const VERSION = 1;
const RANDOM_KEY_VERSION = 2;
const ITERATIONS = 600_000;
const encoder = new TextEncoder();

export type EncryptedIncidentBrief = {
  format: typeof FORMAT;
  version: typeof VERSION;
  encryption: "AES-256-GCM";
  kdf: { name: "PBKDF2-HMAC-SHA-256"; iterations: number; salt: string };
  iv: string;
  ciphertext: string;
};

export type RandomKeyIncidentBrief = {
  format: typeof FORMAT;
  version: typeof RANDOM_KEY_VERSION;
  encryption: "AES-256-GCM";
  key_encoding: "base64url-256-bit";
  iv: string;
  ciphertext: string;
};

const toBase64 = (bytes: Uint8Array): string => {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 8192) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
  }
  return btoa(binary);
};

const fromBase64 = (value: string, expectedLength?: number): Uint8Array<ArrayBuffer> => {
  if (!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value)) {
    throw new Error("The encrypted report contains invalid binary data.");
  }
  const binary = atob(value);
  if (expectedLength !== undefined && binary.length !== expectedLength) {
    throw new Error("The encrypted report has an invalid salt or nonce.");
  }
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
};

const deriveKey = async (passphrase: string, salt: Uint8Array<ArrayBuffer>, iterations: number) => {
  const baseKey = await crypto.subtle.importKey("raw", encoder.encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", hash: "SHA-256", salt, iterations },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
};

const additionalData = encoder.encode(`${FORMAT}:v${VERSION}`);
const randomKeyAdditionalData = encoder.encode(`${FORMAT}:v${RANDOM_KEY_VERSION}`);

const decodeReportKey = (value: string): Uint8Array<ArrayBuffer> => {
  const cleaned = value.trim();
  if (!/^[A-Za-z0-9_-]{43}$/.test(cleaned)) {
    throw new Error("Enter the 43-character report key shared by the sender.");
  }
  return fromBase64(cleaned.replace(/-/g, "+").replace(/_/g, "/") + "=", 32);
};

export async function encryptIncidentBriefWithKey(report: object): Promise<{ envelope: RandomKeyIncidentBrief; reportKey: string }> {
  if (!crypto?.subtle) throw new Error("This browser does not support secure report encryption.");
  const keyBytes = crypto.getRandomValues(new Uint8Array(32));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await crypto.subtle.importKey("raw", keyBytes, { name: "AES-GCM" }, false, ["encrypt"]);
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv, additionalData: randomKeyAdditionalData }, key, encoder.encode(JSON.stringify(report)),
  );
  return {
    envelope: {
      format: FORMAT,
      version: RANDOM_KEY_VERSION,
      encryption: "AES-256-GCM",
      key_encoding: "base64url-256-bit",
      iv: toBase64(iv),
      ciphertext: toBase64(new Uint8Array(ciphertext)),
    },
    reportKey: toBase64(keyBytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""),
  };
}

export async function encryptIncidentBrief(report: object, passphrase: string): Promise<EncryptedIncidentBrief> {
  if (!crypto?.subtle) throw new Error("This browser does not support secure report encryption.");
  if (passphrase.length < 16) throw new Error("Use a passphrase of at least 16 characters.");
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(passphrase, salt, ITERATIONS);
  const plaintext = encoder.encode(JSON.stringify(report));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv, additionalData }, key, plaintext);
  return {
    format: FORMAT,
    version: VERSION,
    encryption: "AES-256-GCM",
    kdf: { name: "PBKDF2-HMAC-SHA-256", iterations: ITERATIONS, salt: toBase64(salt) },
    iv: toBase64(iv),
    ciphertext: toBase64(new Uint8Array(ciphertext)),
  };
}

export async function decryptIncidentBrief(input: unknown, passphrase: string): Promise<Record<string, unknown>> {
  if (!crypto?.subtle) throw new Error("This browser does not support secure report decryption.");
  if (!input || typeof input !== "object") throw new Error("This is not an encrypted CYBERMIND incident brief.");
  const randomEnvelope = input as Partial<RandomKeyIncidentBrief>;
  if (randomEnvelope.version === RANDOM_KEY_VERSION) {
    if (randomEnvelope.format !== FORMAT || randomEnvelope.encryption !== "AES-256-GCM" ||
        randomEnvelope.key_encoding !== "base64url-256-bit" || typeof randomEnvelope.iv !== "string" ||
        typeof randomEnvelope.ciphertext !== "string" || randomEnvelope.ciphertext.length < 24) {
      throw new Error("This is not a supported encrypted CYBERMIND incident brief.");
    }
    const iv = fromBase64(randomEnvelope.iv, 12);
    const ciphertext = fromBase64(randomEnvelope.ciphertext);
    const key = await crypto.subtle.importKey("raw", decodeReportKey(passphrase), "AES-GCM", false, ["decrypt"]);
    try {
      const plaintext = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv, additionalData: randomKeyAdditionalData }, key, ciphertext,
      );
      const report: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(plaintext));
      if (!report || typeof report !== "object" || Array.isArray(report) ||
          (report as Record<string, unknown>).report_type !== "CYBERMIND_Incident_Brief") {
        throw new Error("The decrypted file is not a CYBERMIND incident brief.");
      }
      return report as Record<string, unknown>;
    } catch (error) {
      if (error instanceof Error && error.message === "The decrypted file is not a CYBERMIND incident brief.") throw error;
      throw new Error("Decryption failed. Check the report key and confirm the file has not been altered.");
    }
  }
  const envelope = input as Partial<EncryptedIncidentBrief>;
  if (envelope.format !== FORMAT || envelope.version !== VERSION || envelope.encryption !== "AES-256-GCM" ||
      envelope.kdf?.name !== "PBKDF2-HMAC-SHA-256" || envelope.kdf.iterations !== ITERATIONS ||
      typeof envelope.kdf.salt !== "string" || typeof envelope.iv !== "string" ||
      typeof envelope.ciphertext !== "string" || envelope.ciphertext.length < 24) {
    throw new Error("This is not a supported encrypted CYBERMIND incident brief.");
  }
  const salt = fromBase64(envelope.kdf.salt, 16);
  const iv = fromBase64(envelope.iv, 12);
  const ciphertext = fromBase64(envelope.ciphertext);
  const key = await deriveKey(passphrase, salt, ITERATIONS);
  try {
    const plaintext = await crypto.subtle.decrypt({ name: "AES-GCM", iv, additionalData }, key, ciphertext);
    const report: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(plaintext));
    if (!report || typeof report !== "object" || Array.isArray(report) ||
        (report as Record<string, unknown>).report_type !== "CYBERMIND_Incident_Brief") {
      throw new Error("The decrypted file is not a CYBERMIND incident brief.");
    }
    return report as Record<string, unknown>;
  } catch (error) {
    if (error instanceof Error && error.message === "The decrypted file is not a CYBERMIND incident brief.") throw error;
    throw new Error("Decryption failed. Check the passphrase and confirm the file has not been altered.");
  }
}
