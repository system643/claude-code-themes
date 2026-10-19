# Signing the installers

Unsigned, the app still installs, but:
- **Windows** shows the SmartScreen "Windows protected your PC" screen (click "More info", then "Run anyway");
- **macOS** blocks un-notarized apps (right-click, then "Open" the first time).

For a wide release, signing is worth it.

## Windows

1. Get a code-signing certificate (OV or EV), or use Azure Trusted Signing.
2. Export the certificate as a `.pfx`, convert it to base64 and add it to the repository secrets as `WINDOWS_CERTIFICATE`.
3. Set `bundle.windows.certificateThumbprint` in `app/src-tauri/tauri.conf.json` (see Tauri's "Windows Code Signing" guide).

## macOS

1. An Apple Developer account ($99/year) and a "Developer ID Application" certificate.
2. Repository secrets: `APPLE_CERTIFICATE` (p12 as base64), `APPLE_CERTIFICATE_PASSWORD`, `APPLE_ID`, `APPLE_PASSWORD` (an app-specific password), `APPLE_TEAM_ID`.
3. The `release.yml` workflow already passes them to `tauri-action`, which signs and notarizes.

## Publishing a version

```
git tag v0.3.0
git push origin v0.3.0
```

The workflow builds the installers for all three systems and prepares a draft release to review before publishing. Then update `packaging/winget` and `packaging/homebrew` with the new SHA256 checksums.
