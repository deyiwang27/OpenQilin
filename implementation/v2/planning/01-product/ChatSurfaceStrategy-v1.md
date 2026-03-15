# Chat Surface Strategy

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Define the near-term and longer-term chat surface strategy for OpenQilin.
- Make the current conclusion explicit instead of leaving it scattered across discussion.
- Keep the choice aligned with OpenQilin's product thesis, MVP-v2 scope, and free-account constraint.

## 2. Framing

OpenQilin is built for the solopreneur: turning one capable person into a coordinated AI-augmented team.
It does this through governed role delegation, project-centered execution, and explicit control over authority, budget, and evidence.

For MVP-v2, the practical constraint is:
- prefer free-account-friendly chat surfaces
- keep setup and operator friction low
- avoid broad multi-channel scope before the core operating model is strong

## 3. Conclusion

For the current strategy, only two chat surfaces should be considered:

- `Discord` for MVP-v2
- `Telegram` as the next future adapter candidate

Other chat surfaces may matter later, but they should not be part of the near-term surface strategy.

## 4. Why Discord for MVP-v2

Discord remains the best fit for MVP-v2 because:
- normal usage is free
- the app/developer flow is accessible
- servers, channels, threads, roles, pins, and DMs map well to OpenQilin's institutional and project-space model
- it supports the current MVP-v2 design around:
  - institutional surfaces
  - project channels/threads
  - Secretary DM
  - leadership channel summaries and alerts
  - dashboard-link pinning

Strategically:
- Discord gives enough structure for OpenQilin's governed operating model
- Discord is already the current implementation direction
- staying Discord-first keeps scope controlled

## 5. Why Telegram Is the Future Free-First Candidate

Telegram is the strongest next adapter under a free-account strategy because:
- the bot platform is free for users and developers
- the Bot API is mature and straightforward
- Telegram has lower platform friction than more enterprise-heavy chat surfaces
- it is a strong candidate for future bot-first or mobile-friendly interaction

Telegram should be treated as:
- the next serious adapter to consider after Discord
- a future expansion target, not part of MVP-v2 primary scope

## 6. Why Not Prioritize Others Right Now

### 6.1 Slack

Slack is a strong product surface in general, but not the right free-first priority now because:
- free plan history is limited
- free plan app limits create extra friction
- workspace/admin overhead is heavier than Discord or Telegram

Slack is worth reconsidering later if:
- OpenQilin matures into a stronger work-console product
- paid or business-oriented deployment becomes a real target

### 6.2 WhatsApp

WhatsApp is not a good primary OpenQilin surface for this stage because:
- it is more useful for alerts and lightweight interaction than rich project operations
- it is not the cleanest surface for governed project-space workflows
- it is less aligned with the current institutional/project channel model

### 6.3 Teams

Teams is more enterprise-oriented than OpenQilin's current target.

That makes it lower priority for a solopreneur-focused MVP-v2.

### 6.4 WeChat / WeCom

These should only become a priority if China-oriented distribution becomes a real product strategy.

They are not the right near-term priority for the current MVP-v2 direction.

## 7. Recommended Surface Roadmap

### 7.1 MVP-v2

- Primary surface: `Discord`
- Dashboard: OpenQilin-owned web UI
- Secretary DM: private alert and explanation inbox
- `leadership_council`: shared summaries, dashboard link, and severity-based shared alerts

### 7.2 Post-MVP-v2

- First external chat expansion candidate: `Telegram`
- Keep the same governance, routing, and project-space abstractions where possible
- Treat Telegram as an adapter, not as a reason to redesign product semantics

### 7.3 Longer term

- OpenQilin-owned console becomes the more important primary operator surface
- external chat apps become adapters for:
  - notifications
  - lightweight interaction
  - portability

## 8. Strategy Principle

The correct strategy is not:
- support every chat platform as early as possible

The correct strategy is:
- make one chat surface excellent
- make the dashboard/console useful
- then add one free-first secondary adapter

For now, that means:
- `Discord now`
- `Telegram later`

## 9. Bottom Line

Yes, I agree with the narrowed conclusion:

- only `Discord` and `Telegram` should be considered in the current planning horizon
- `Discord` is the MVP-v2 choice
- `Telegram` is the future free-first expansion candidate
- broader chat expansion should wait until the Discord model and operator console/dashboard are strong

## 10. Sources

- Discord developer quickstart: https://docs.discord.com/developers/quick-start/getting-started
- Telegram bot platform introduction: https://core.telegram.org/bots
- Telegram Bot API: https://core.telegram.org/bots/api
- Slack free plan: https://slack.com/pricing/free
- Slack free-plan limitations: https://slack.com/help/articles/27204752526611-Feature-limitations-on-the-free-version-of-Slack
