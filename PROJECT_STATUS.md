# Project status
Date: 2026-11-27

Historical accepted Lean baseline: 0.2.0 (`.governance-version`); imported skill source: central 0.2.6. The central completion audit records adoption and successful deployment at `eec3b8fd36b1ef7ac4bf49b9bbe804f4477179c2` (run 45863821774); this is recorded historical evidence, not a fresh deployment observation. The previous “not adopted” wording was stale.

Prepared governance corrections correspond to central 0.2.10. They are local/unreleased until reviewed and accepted; this does not claim production runs 0.2.10. Application files, approved design/content and publish-manifest.json are unchanged.

Regular PR validation checks the candidate artifact, local links/resources/navigation and browsers. It does not compare intended candidate edits to old live bytes. Explicit `verify-migration.yml` is manual and requires pinned candidate/baseline revisions: unchanged approved public paths are checked before live byte comparison. For a pre-manifest baseline, this checks approved candidate paths only, not omitted baseline inventory. Deployment validates the staged artifact fail closed, records its SHA-256 inventory before upload, and checks published bytes against that exact inventory afterwards. A postdeploy failure reports an unverified deployment; it does not automatically roll back or change hosting.

Unknown potential public root files produce warnings requiring manifest review; referenced missing assets or navigation targets fail. Never add files to the manifest merely to silence a warning. Internal documents remain excluded. Secret scanning is prepared as a separate redacted CI gate. Existing reviews, design constraints and deployment authorization remain authoritative.

Local synthetic contract tests and staged-source checks are recorded in the central corrections evidence under `docs/audits/evidence/2026-11-27-corrections/wp3`. Hosted CI, actual deployment and physical-device acceptance remain pending; no push, merge, deploy, DNS or authentication change was performed by this work package.
