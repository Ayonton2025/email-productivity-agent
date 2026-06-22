"""
Re-encrypt LLM provider API keys with a new ENCRYPTION_KEY.

Usage examples:
  # Dry run (inspect what would change)
  python -m backend.scripts.reencrypt_llm_keys --new-key NEWKEY --dry-run

  # Actually rotate keys (will modify DB)
  python -m backend.scripts.reencrypt_llm_keys --new-key NEWKEY --confirm

You may pass --old-key if the currently-set ENCRYPTION_KEY is not the one
used to encrypt the existing DB values.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Optional

from app.core.config import settings
from app.models.database import AsyncSessionLocal
from app.services.llm_provider_config_service import LLMProviderConfigService


def _require_confirm(args: argparse.Namespace) -> bool:
    if args.dry_run:
        return True
    return args.confirm


async def _rotate_keys(old_key: Optional[str], new_key: str, provider_filter: Optional[str], dry_run: bool):
    original_key = settings.ENCRYPTION_KEY

    # If an explicit old_key is provided, use it for decryption. Otherwise use current settings.
    if old_key:
        settings.ENCRYPTION_KEY = old_key

    async with AsyncSessionLocal() as session:
        rows = await LLMProviderConfigService.list_configs(session)

        changed = []
        for row in rows:
            if provider_filter and row.provider != provider_filter:
                continue

            encrypted_count = len(row.api_keys_encrypted or [])
            # Decrypt using the (possibly overridden) settings.ENCRYPTION_KEY
            decrypted_keys = LLMProviderConfigService._decrypt_keys(row.api_keys_encrypted or [])
            decryption_failures = max(0, encrypted_count - len(decrypted_keys))

            print(f"Provider: {row.provider} — encrypted_count={encrypted_count}, decrypted_ok={len(decrypted_keys)}, failures={decryption_failures}")

            if not decrypted_keys:
                print("  Skipping (no decrypted keys available)")
                continue

            # Now switch to the new key and re-encrypt
            settings.ENCRYPTION_KEY = new_key
            re_encrypted = LLMProviderConfigService._encrypt_keys(decrypted_keys)

            if re_encrypted == (row.api_keys_encrypted or []):
                print("  No change required (already encrypted with the target key)")
                # Restore old key for next iteration
                if old_key:
                    settings.ENCRYPTION_KEY = old_key
                else:
                    settings.ENCRYPTION_KEY = original_key
                continue

            print(f"  Would replace {len(row.api_keys_encrypted or [])} encrypted entries")

            if dry_run:
                # Restore key and continue
                if old_key:
                    settings.ENCRYPTION_KEY = old_key
                else:
                    settings.ENCRYPTION_KEY = original_key
                continue

            # Apply changes to the DB row
            row.api_keys_encrypted = re_encrypted
            row.updated_at = row.updated_at
            await session.flush()
            changed.append(row.provider)

            # Restore old key for next provider's decryption phase
            if old_key:
                settings.ENCRYPTION_KEY = old_key
            else:
                settings.ENCRYPTION_KEY = original_key

        if changed and not dry_run:
            await session.commit()

        print("\nSummary:")
        print(f"  Providers modified: {len(changed)}")
        for p in changed:
            print(f"   - {p}")

    # Restore original runtime key
    settings.ENCRYPTION_KEY = original_key


def main(argv=None):
    parser = argparse.ArgumentParser(description="Re-encrypt LLM provider API keys with a new ENCRYPTION_KEY")
    parser.add_argument("--old-key", help="Old ENCRYPTION_KEY used to decrypt existing DB values (optional)")
    parser.add_argument("--new-key", required=True, help="New ENCRYPTION_KEY to encrypt keys with")
    parser.add_argument("--provider", help="Limit rotation to a specific provider (e.g., 'openai')")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing to DB")
    parser.add_argument("--confirm", action="store_true", help="Confirm applying changes (required unless --dry-run)")

    args = parser.parse_args(argv)

    if not _require_confirm(args):
        print("Operation not confirmed. Use --confirm to apply changes or --dry-run to preview.")
        parser.print_help()
        sys.exit(2)

    try:
        asyncio.run(_rotate_keys(args.old_key, args.new_key, args.provider, args.dry_run))
    except Exception as e:
        print(f"Error during rotation: {e}")
        raise


if __name__ == "__main__":
    main()
