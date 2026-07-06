# Build Adversarial Challenge

## Round 1 — 2026-07-06
**Model:** opus (Prosecution)

## Fixed
| Sev | Vector | Location | Defect | Fix applied |
|-----|--------|----------|--------|-------------|
| None | | | | |

## Findings (unfixed — require gate decision)
| Sev | Vector | Location | Indictment |
|-----|--------|----------|------------|
| Low | V2 (edge case) | users.py:24 | `User.email.like("%prospect33.com%")` is an unanchored substring match, not a domain match. Admits any address merely containing the string (e.g. `attacker@prospect33.com.evil.io`). Pre-existing and untouched by this diff. Should be `.like("%@prospect33.com")` or explicit endswith. The diff's correctness now leans on this guard more than before. |
| Info | V3 (blast radius) | users.py:23 vs user_service.py:20 | Placeholder-user exclusion is enforced by the email LIKE, not the new `or_(ms_oid, password_hash)` clause (placeholders have both creds NULL, so incidentally excluded by both). Two partially-redundant guards — safe today; noting the coupling. |

**Assessment:** The one-line logic change plus the `or_` import correctly implements the stated plan intent. SSO users (`ms_oid` set, real email) now pass; legacy password users still pass; AI `@pulseops.internal` placeholders (both creds NULL, non-matching email) remain excluded. No defect introduced by the diff itself. The substring-LIKE weakness is pre-existing and out of burst scope — candidate for DEFERRED.
