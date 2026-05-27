# Security Guide

This document covers the security features and best practices for The Memory Vault.

## Security Features Overview

The Memory Vault implements multiple layers of security:

1. **AES-256 Encryption** - All snapshots encrypted at rest
2. **WORM Immutability** - Object Lock prevents deletion
3. **RM-Shield** - Protection against accidental file deletion
4. **Secure Credential Storage** - Local configuration file

## Encryption

### Restic Encryption

All snapshots created by The Memory Vault are encrypted using Restic's built-in AES-256 encryption.

**Key Points:**
- Encryption happens locally before data leaves your machine
- The encryption password is never sent to Wasabi
- Each snapshot is independently encrypted
- Decryption requires the password from your config file

**Best Practices:**
- Use a strong, unique encryption password
- Store your encryption password in a secure location (password manager)
- Don't share your config file with others
- Consider backing up your config file separately

### Wasabi S3 Encryption

Wasabi also provides server-side encryption (SSE-S3 or SSE-KMS). This is in addition to Restic's encryption.

**Note:** Client-side encryption (Restic) is always used regardless of Wasabi's server-side encryption.

## WORM Immutability (Object Lock)

### What is WORM?

WORM (Write Once, Read Many) ensures that once data is written, it cannot be modified or deleted for a specified retention period.

### How It Works

1. During setup, you can enable Object Lock with a retention period (default: 90 days)
2. The application configures Wasabi Object Lock via API
3. All objects in the bucket become immutable for the retention period
4. Even if someone has your credentials, they cannot delete data

### Benefits

- **Ransomware Protection:** Attackers cannot delete your backups
- **Accidental Deletion:** Prevents `rm -r` disasters
- **Compliance:** Meets data retention requirements
- **Cost-Effective:** Wasabi charges 90-day minimum regardless, so no extra cost

### Limitations

- Cannot delete snapshots during retention period
- Must plan retention period carefully
- Requires bucket to be created with Object Lock enabled

### Cost Considerations

Wasabi has a 90-day minimum retention policy:
- If you delete a file after 10 days, you still pay for 80 days
- With Object Lock, the file stays available for the full 90 days
- **Conclusion:** Object Lock provides protection without additional cost

## RM-Shield

### What is RM-Shield?

RM-Shield replaces the dangerous `rm` command with `trash-put`, moving files to the trash instead of permanently deleting them.

### How It Works

1. When enabled, it adds aliases to `.bashrc` and `.zshrc`:
   ```bash
   alias rm='trash-put'
   alias rrm='/bin/rm'
   ```
2. It also adds a warning when you're inside the vault mount point
3. You can still force delete with `rrm`

### Enabling RM-Shield

```bash
vault shield --on
```

### Disabling RM-Shield

```bash
vault shield --off
```

### Checking Status

```bash
vault shield
```

## Credential Security

### Configuration File

Credentials are stored in `~/.config/memory-vault/config.json`:

```json
{
  "storage": {
    "access_key": "YOUR_ACCESS_KEY",
    "secret_key": "YOUR_SECRET_KEY"
  }
}
```

**Security Recommendations:**
- Set file permissions: `chmod 600 ~/.config/memory-vault/config.json`
- Don't commit config file to version control
- Use restricted Wasabi credentials (bucket-specific if possible)
- Rotate credentials periodically

### Wasabi Best Practices

1. **Use Bucket-Specific Policies:** Create IAM policies that only allow access to specific buckets
2. **Enable MFA:** Enable multi-factor authentication on your Wasabi account
3. **Monitor Access:** Regularly check Wasabi access logs
4. **Use Least Privilege:** Only grant necessary permissions

## Network Security

### Data in Transit

- All data to/from Wasabi is encrypted via HTTPS (TLS 1.2+)
- Rclone uses secure S3 protocol
- No plaintext credentials are transmitted

### Firewall Considerations

Allow outbound connections to:
- `s3.*.wasabisys.com` (Wasabi S3 endpoints)
- `rclone.org` (for updates, if using rclone's update feature)

## Backup and Recovery

### Backup Your Config

Your `config.json` contains:
- Wasabi credentials
- Encryption password for Restic

**Critical:** Without this file, you cannot access your snapshots.

**Backup Strategy:**
1. Copy `~/.config/memory-vault/config.json` to a secure location
2. Store in a password manager or encrypted USB drive
3. Test restoration periodically

### Recovery Process

If you lose your config file:
1. Restore config.json from backup
2. Run `vault status` to verify connectivity
3. Run `vault list` to verify snapshot access

## Security Auditing

### Review Access Logs

Wasabi provides access logs. Regularly review for:
- Unusual IP addresses
- Failed authentication attempts
- Unexpected access patterns

### Check Mount Status

```bash
vault status
```

Verify that the vault is only mounted when expected.

## Common Security Mistakes

### ❌ Don't

- Share your config file
- Use weak encryption passwords
- Disable Object Lock for convenience
- Ignore RM-Shield warnings
- Store credentials in plain text elsewhere

### ✅ Do

- Use strong, unique passwords
- Enable Object Lock
- Enable RM-Shield
- Regularly review access logs
- Backup your config file
- Rotate credentials periodically

## Security Checklist

- [ ] Strong encryption password set
- [ ] Object Lock enabled (90-day retention)
- [ ] RM-Shield enabled
- [ ] Config file backed up
- [ ] Config file permissions set to 600
- [ ] Wasabi MFA enabled
- [ ] Bucket-specific IAM policy configured
- [ ] Access logs reviewed regularly
- [ ] Credentials rotated periodically
- [ ] Tested recovery process

## Reporting Security Issues

If you discover a security vulnerability, please report it privately:
- GitHub Security Advisory: https://github.com/Daniquir/memory-vault/security/advisories
- Do not open public issues
- Include steps to reproduce
- Allow time for fix before disclosure
