# AstroLink release and security notes

## Downloads

Tagged GitHub releases contain platform-specific binaries and SHA-256 checksum files:

- `AstroLink-windows-x64.exe`
- `AstroLink-linux-x64`
- `AstroLink-macos-x64`

The binaries are built from the tagged source by GitHub Actions. The build disables UPX because compressed PyInstaller executables are more likely to trigger antivirus heuristics.

## Windows Defender and trust

No unsigned executable can be guaranteed to be accepted by every Defender installation. AstroLink does not use stealth, persistence, obfuscation, privilege escalation, registry autoruns, or network beacons. Defender reputation warnings can still happen for a new unsigned PyInstaller binary.

For a production Windows release, the maintainer must sign the executable with an organization-owned Authenticode certificate and publish the certificate chain. The certificate private key must stay in a protected CI secret or hardware-backed signing service; it must never be committed to this repository.

Verify the download before running it:

```powershell
Get-FileHash .\AstroLink-windows-x64.exe -Algorithm SHA256
Get-Content .\AstroLink-windows-x64.exe.sha256
```

Only run the binary when the hashes match the release checksum. If Windows SmartScreen shows an unknown-publisher warning, verify the hash and use the official tagged GitHub release rather than disabling Defender globally.

## Local privacy

AstroLink processes frames locally by default. It does not upload images to a cloud service unless the user explicitly configures a remote server or runs the camera bridge against one. Firebase authentication is optional and is not required for local field mode.

## First run

The desktop executable starts a local server on port 8080 and opens the browser on the same computer. To let a phone view the station, allow the executable through the operating system firewall on the private/local network only. Do not expose port 8080 directly to the public internet without `ASTROLINK_API_TOKEN`, `ASTROLINK_ADMIN_TOKEN`, and an HTTPS reverse proxy.

## macOS and Linux

macOS may require an explicit executable permission:

```bash
chmod +x AstroLink-macos-x64
./AstroLink-macos-x64
```

Linux:

```bash
chmod +x AstroLink-linux-x64
./AstroLink-linux-x64
```

Unsigned macOS binaries may require the user to approve the application in Privacy & Security. A notarized macOS distribution requires an Apple Developer account and signing secrets, which are intentionally not stored in this repository.
