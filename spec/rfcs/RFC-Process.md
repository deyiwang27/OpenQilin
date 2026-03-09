# OpenQilin - RFC Spike Process

## 1. Purpose
- Define a timeboxed investigation method for tool selection before architecture baseline lock.

## 2. Timebox and Output
- Timebox: 1-2 weeks per RFC spike.
- Required decision output: `adopt`, `defer`, or `adopt_later`.

## 3. Mandatory RFC Sections
- target use-cases
- integration architecture
- failure and security risks
- cost profile
- conformance impact
- recommendation and rationale
- migration/rollback notes

## 4. Required RFC Pack
- `spec/rfcs/RFC-01-Orchestration-Governance-ControlPlane.md`
- `spec/rfcs/RFC-02-Memory-Intelligence-Observability.md`
- `spec/rfcs/RFC-03-Language-Runtime-Persistence-Deployment.md`
- `spec/rfcs/RFC-04-Data-Memory-Architecture.md`
- `spec/rfcs/RFC-05-Deployment-and-Cost-Strategy.md`

## 5. Completion Gate
- Every required domain has one recorded recommendation.
- Every recommendation includes explicit impact on OpenQilin conformance model.
