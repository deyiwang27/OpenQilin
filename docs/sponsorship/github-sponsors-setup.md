# GitHub Sponsors — Repo Setup Guide

This guide records the repository changes needed for GitHub Sponsors on the `deyiwang27` account to appear correctly on OpenQilin.

**Current status:** GitHub Sponsors is set up for the account. This repo is wired to that profile.

---

## Repo wiring checklist

1. Add `.github/FUNDING.yml` on the default branch with:

```yaml
github: [deyiwang27]
```

2. Confirm the repository remote is `https://github.com/deyiwang27/OpenQilin.git`
3. Add a visible Sponsors link in `README.md`
4. Verify the public repo header shows the **Sponsor** button

---

## Verification

After pushing the default branch:

1. Open: https://github.com/deyiwang27/OpenQilin
2. Confirm the **Sponsor** button appears in the repository header
3. Click it and confirm it opens `https://github.com/sponsors/deyiwang27`

---

## Public profile copy

The public summary for the GitHub Sponsors profile lives in:

- `docs/sponsorship/project-summary.md`

Update it when tiers, goals, or funding use change.
