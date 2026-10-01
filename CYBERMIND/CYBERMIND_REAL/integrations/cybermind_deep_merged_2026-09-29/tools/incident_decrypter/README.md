# CYBERMIND offline incident brief decrypter

Open `index.html` directly in a modern browser, visit `/incident-decrypter` in the CYBERMIND app, or run the separate `incident-decrypter` Docker Compose service at `http://127.0.0.1:8001/`. This tool needs no model, account, API, or network access after the static page is loaded. It accepts encrypted CYBERMIND incident-brief JSON files (up to 20 MB) and the separately supplied report key. It previews the decrypted JSON and can download a readable JSON copy. The readable copy is no longer encrypted.

New exports use a fresh, random 256-bit AES-GCM key for every report. The key is shown once after export and is **not** included in the encrypted JSON. Share it via a separate trusted channel. A recipient cannot decrypt the report without that key. Legacy PBKDF2 passphrase exports (version 1) are also supported. Neither the browser tool nor the app stores the key. Browser clipboard history may retain it after copying.

The encryption code from the SIH 2025 example informed the random-key and AES-GCM approach, but this implementation does not return the secret and ciphertext together in one export, does not use its unused salt, and does not require its SQLCipher server or an online service.
