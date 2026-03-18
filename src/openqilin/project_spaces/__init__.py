"""Project Space Binding and Routing — M13-WP3.

Provides:
- ProjectSpaceBinding model and BindingState lifecycle enum
- PostgresProjectSpaceBindingRepository for durable binding persistence
- DiscordChannelAutomator for channel lifecycle operations
- ProjectSpaceBindingService for create-and-bind / state transition
- ProjectSpaceRoutingResolver for channel → project context resolution
"""
