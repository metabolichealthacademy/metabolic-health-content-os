# Publishing destination registry — owner-supplied candidates

The accompanying `publishing-destinations.json` records public links supplied in chat. It does **not** connect OAuth accounts or enable posting. Do not store access tokens in this file.

## Brand separation
- **Metabolic Health Academy:** main website and @themetabolichealthacademy Instagram.
- **Ask the Metabolic Doctor:** Substack, @askthemetabolicdoctor Instagram, and @askmetabolicdr X.
- **Unconfirmed brand association:** Facebook profile ID `61594829624891`.
- **Missing:** YouTube channel handle or URL; the message introduced YouTube but did not give a channel URL.

## Mandatory next steps
1. Verify ownership, rights, and brand-to-channel mapping for each candidate. Keep all disabled by default.
2. Collect YouTube channel URL or handle; identify the intended Facebook profile/page.
3. Use platform-approved account authorization, with minimal scopes and secrets stored outside source control.
4. Implement distinct content approval and publish approval: exact script revision, caption, assets, platform, destination account and timestamp, with audited authenticated owner approval.
5. Before posting, show a per-account preview; reject on missing/expired approval or any changed asset/caption/destination. Do not post to Ask the Metabolic Doctor from MHA approval alone.
6. Test drafts and idempotency without making public posts. Require a fresh explicit authorization for every release.
7. Never enable a platform solely because a public URL is supplied.

The existing publishing gate in PR #19 is still a draft at the time this registry was prepared. This registry must not imply deployment or completed publishing integration.
