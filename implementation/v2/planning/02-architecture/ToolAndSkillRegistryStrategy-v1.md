# Tool and Skill Registry Strategy

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Define the strategy for tools and skills in OpenQilin.
- Clarify how OpenQilin should interact with public tool/skill ecosystems.
- Make quality, safety, and registration workflow explicit before MVP-v2 implementation expands capabilities.

## 2. Framing

OpenQilin already has the right high-level direction in local specs:
- `MCP` as the transport/interoperability layer for tools
- `Skills` as the internal governance wrapper over tool/model capabilities

Relevant local references:
- [SkillCatalogAndBindings.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/spec/orchestration/registry/SkillCatalogAndBindings.md)
- [ToolRegistry.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/spec/orchestration/registry/ToolRegistry.md)
- [RFC-01-Orchestration-Governance-ControlPlane.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/spec/rfcs/RFC-01-Orchestration-Governance-ControlPlane.md)
- [RFC-02-Memory-Intelligence-Observability.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/spec/rfcs/RFC-02-Memory-Intelligence-Observability.md)

This means OpenQilin should not treat external registries as authoritative runtime policy.

The correct model is:
- external registries are `discovery sources`
- OpenQilin's internal tool and skill registries remain `authoritative`

## 3. Tool vs Skill

OpenQilin should keep these concepts separate:

### 3.1 Tool

A tool is an executable capability surface:
- internal function
- external API integration
- MCP server capability
- sandboxed command or workflow

Tools answer:
- what can be called
- where it runs
- what network/sandbox it needs

### 3.2 Skill

A skill is a governed capability package:
- intent
- allowed tools
- allowed model classes
- budget class
- safety constraints
- escalation obligations

Skills answer:
- when a capability is allowed
- who can use it
- under what constraints

## 4. External Ecosystem Reality

There are already public registries and hubs for tools/skills.

### 4.1 MCP Registry

The official MCP Registry is now live in preview and acts as the authoritative metadata repository for publicly-available MCP servers.

Important details:
- it is a `metadata registry`, not a code-hosting registry
- package code may still live in npm, PyPI, Docker, GitHub Releases, and other package hosts
- the registry is in `preview`
- the official docs explicitly note that subregistries may add ratings and security scanning

Implication:
- the official registry is useful for discovery
- it is not itself a complete trust or safety layer

### 4.2 ClawHub / OpenClaw skill ecosystem

ClawHub is the public skill registry for OpenClaw.

Important details from the official docs:
- it is a free service
- all skills are public and visible
- anyone can upload, subject to a minimal GitHub-account-age gate
- users can report unsafe or abusive skills

Implication:
- ClawHub is useful as a discovery ecosystem
- it is explicitly open by default
- it should not be trusted as a governed source of truth for OpenQilin

### 4.3 Smithery

Smithery provides a registry model around MCP servers and skills.

Important currently visible details:
- namespaces have a `Hobby (free)` tier with limited namespaces
- skills can be searched with fields such as `qualityScore` and `verified`
- skills can be linked from GitHub repositories containing `SKILL.md`

Implication:
- Smithery is useful as a discovery and packaging reference
- its metadata is helpful
- but OpenQilin still needs its own acceptance and governance process

## 5. Cost and Licensing Reality

Most external tool/skill registries are free to browse.

But "free registry" does not mean "free capability."

OpenQilin should assume a candidate tool or skill may introduce:
- paid third-party API requirements
- cloud or hosting costs
- secret-management requirements
- restrictive licenses
- runtime/network risk

Therefore:
- no external tool or skill should be accepted into OpenQilin purely because the registry entry is public and free to view

## 6. Strategy

## 6.1 Internal registry stays authoritative

OpenQilin should keep:
- an internal `tool_registry`
- an internal `skill_registry`
- explicit bindings between:
  - role
  - skill
  - tool
  - model class
  - sandbox/network policy

External registries should never bypass this.

## 6.2 External registries are discovery-only

OpenQilin may search or inspect external ecosystems such as:
- official MCP Registry
- Smithery
- ClawHub
- GitHub repositories

But discovery should not equal activation.

The safe rule is:
- `discover externally`
- `review internally`
- `register internally`
- `activate only after approval`

## 6.3 Use registry trust tiers

I recommend four trust tiers inside OpenQilin:

### A. Core trusted

- bundled or first-party maintained
- reviewed and fully governed
- allowed in normal production paths

### B. Reviewed community

- sourced externally
- inspected and approved
- registered with explicit limits and pinned versions

### C. Experimental / quarantine

- candidate capability under review
- only usable in isolated test paths
- not available to normal governed execution

### D. Blocked / rejected

- known unsafe
- incompatible
- failed review
- explicitly denied from future reuse

## 7. Quality and Safety Controls

## 7.1 Minimum acceptance checks

Every external candidate tool or skill should go through checks for:
- source location
- maintainer identity or namespace
- license
- version and changelog
- required secrets
- required network access
- declared dependencies
- execution model

## 7.2 Security review

At minimum, OpenQilin should inspect:
- install method
- shell/script execution behavior
- filesystem access expectations
- external network destinations
- credential requirements
- transitive dependency risk where relevant

## 7.3 Governance review

Before activation, OpenQilin should define:
- which roles may use it
- which skills may bind to it
- budget class
- sandbox profile
- network policy
- whether it is read-only, write-capable, or privileged

## 7.4 Sandbox and least privilege

No external capability should automatically receive:
- unrestricted network
- unrestricted filesystem access
- unrestricted mutation authority

Skills and tools should be mapped to least-privilege runtime profiles.

## 7.5 Version pinning and rollback

Accepted tools and skills should be:
- version pinned
- content hashed where practical
- reversible/rollbackable
- auditable in change history

## 7.6 Testing before activation

Before any non-trivial capability is activated:
- run it in a sandbox or test harness
- verify expected behavior
- confirm failure modes
- confirm logging and traceability

## 8. Recommended Acquisition Workflow

If a Specialist or other role needs a capability that is not available in OpenQilin's internal registry, the workflow should be:

### Step 1. Capability gap request

The requesting role does not install anything directly.

Instead it raises a structured request containing:
- missing capability description
- intended use case
- project context if relevant
- urgency
- expected tool/skill type

### Step 2. Research phase

An approved research path searches:
- official MCP Registry
- Smithery
- ClawHub
- GitHub

This should be done by a governed research flow, not by direct auto-install.

Expected output:
- candidate list
- source links
- license notes
- trust signals
- risk notes
- whether the capability appears active/maintained

### Step 3. Review and selection

OpenQilin selects a candidate only after review of:
- safety
- fit
- maintenance quality
- cost implications
- integration complexity

### Step 4. Quarantine import

The chosen candidate enters an internal quarantine stage:
- download or vendor reference
- inspect files
- run static checks where possible
- validate runtime assumptions

### Step 5. Internal registration

Only after review does OpenQilin create:
- internal `tool_registry` entry
- internal `skill_registry` entry or binding update
- explicit role/skill/tool policy mapping

### Step 6. Controlled activation

Activation should be scoped:
- to specific roles
- to specific skills
- possibly to specific projects first

### Step 7. Ongoing monitoring

After activation, OpenQilin should monitor:
- failures
- cost drift
- policy denials
- suspicious behavior
- maintenance/update needs

## 9. What the Specialist Agent Should Be Allowed to Do

A Specialist should be allowed to:
- identify a capability gap
- recommend that a new skill/tool is needed
- research candidates through approved discovery paths
- submit a structured proposal

A Specialist should not be allowed to:
- directly install arbitrary external tools
- directly register a skill into production registry
- bypass policy review
- self-authorize privileged capabilities

This is important. Capability expansion is a governance action, not just a convenience action.

## 10. MVP-v2 Recommendation

For MVP-v2, keep the strategy narrow:

- do not build a broad public auto-install marketplace into OpenQilin
- keep the internal registry authoritative
- support external discovery only as a reviewed workflow
- start with first-party or tightly reviewed capabilities
- treat external community skills/tools as optional intake candidates, not default dependencies

This is the right tradeoff for:
- safety
- product clarity
- cost control
- governance integrity

## 11. Bottom Line

The correct OpenQilin strategy is:

- `MCP for interoperability`
- `Skills for governance`
- `external registries for discovery`
- `internal registry for authority`

Yes, many public registries are free to browse or use.
No, that does not make them trustworthy enough for direct governed activation.

If a Specialist needs a missing capability, the system should support:
- proposing
- researching
- reviewing
- quarantining
- registering
- activating

But not:
- auto-installing into production by default

## 12. Sources

- Official MCP Registry overview: https://modelcontextprotocol.io/registry/about
- MCP Registry reference and API: https://registry.modelcontextprotocol.io/
- MCP Registry aggregators: https://modelcontextprotocol.io/registry/registry-aggregators
- MCP Registry publishing/authentication: https://modelcontextprotocol.io/registry/authentication
- MCP official examples / servers repo references: https://modelcontextprotocol.io/examples
- ClawHub official docs: https://docs.openclaw.ai/tools/clawhub
- Smithery namespaces: https://smithery.ai/docs/concepts/namespaces
- Smithery skills search API: https://smithery.ai/docs/api-reference/skills/list-or-search-skills
- Smithery create skill from GitHub repo: https://smithery.ai/docs/api-reference/skills/create-a-new-skill-deprecated
