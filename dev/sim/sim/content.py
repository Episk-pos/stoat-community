"""Random content generation for simulated activity."""

from __future__ import annotations

import random

MESSAGES = [
    # Casual chat
    "Hey, how's it going?",
    "Anyone around?",
    "Good morning everyone!",
    "brb, grabbing coffee",
    "lol that's great",
    "agreed, makes sense to me",
    "nice work!",
    "thanks for sharing that",
    "I was just thinking the same thing",
    "haha yeah",
    "sounds good to me",
    "let me know if you need help with that",
    "no worries, take your time",
    "that's a good point actually",
    "oh interesting, I didn't know that",

    # Technical
    "Has anyone tried the new API endpoint?",
    "The build is looking good on staging",
    "I pushed a fix for that bug we discussed",
    "The tests are passing now",
    "Can someone review my PR when they get a chance?",
    "I'm seeing some weird behavior with the websocket connection",
    "The database migration ran smoothly",
    "We should probably add some error handling there",
    "I refactored the auth middleware, much cleaner now",
    "Deployed the latest changes to dev",

    # Links and references
    "Check this out: https://example.com/interesting-article",
    "Related issue: https://github.com/example/repo/issues/42",
    "Docs are here: https://docs.example.com/getting-started",
    "Found a useful resource: https://stackoverflow.com/q/12345",
    "This library looks promising: https://github.com/example/cool-lib",

    # Questions
    "What do you think about the new design?",
    "Is the staging environment up?",
    "When's the next release scheduled?",
    "Does anyone know why the CI is slow today?",
    "Should we use WebSocket or SSE for this?",
    "What's the best way to handle this edge case?",

    # Code snippets
    "```\nconst result = await fetch('/api/data');\nconsole.log(result);\n```",
    "Try running `npm run dev` and see if it works",
    "The fix is just changing `==` to `===` on line 42",
    "You can use `git rebase -i HEAD~3` to squash those commits",

    # Longer messages
    "I've been thinking about the architecture and I think we should split this into two services. The current monolith is getting hard to maintain and deploy independently.",
    "Just finished the performance audit. Main bottleneck is the database queries in the message handler. We could add an index on the channel_id field to speed things up significantly.",
    "Quick update on the mobile app: the new navigation is working well, but we still need to fix the notification badge count. Should have a PR up by end of day.",
]

EMOJI_REACTIONS = [
    "✅", "👍", "❤️", "😂", "🎉", "🔥", "👀", "💯",
    "🚀", "⭐", "🤔", "👏", "💪", "🙌", "😍", "🤣",
]

USER_POOL = [
    ("sim-alice", "Alice Sim"),
    ("sim-bob", "Bob Sim"),
    ("sim-carol", "Carol Sim"),
    ("sim-dave", "Dave Sim"),
    ("sim-eve", "Eve Sim"),
    ("sim-frank", "Frank Sim"),
    ("sim-grace", "Grace Sim"),
    ("sim-heidi", "Heidi Sim"),
    ("sim-ivan", "Ivan Sim"),
    ("sim-judy", "Judy Sim"),
    ("sim-karl", "Karl Sim"),
    ("sim-lily", "Lily Sim"),
    ("sim-mike", "Mike Sim"),
    ("sim-nina", "Nina Sim"),
    ("sim-oscar", "Oscar Sim"),
    ("sim-pat", "Pat Sim"),
    ("sim-quinn", "Quinn Sim"),
    ("sim-rosa", "Rosa Sim"),
    ("sim-sam", "Sam Sim"),
    ("sim-tina", "Tina Sim"),
]

# Fixed ULID-style IDs for sim users (deterministic, idempotent)
# 26-char alphanumeric, starting with 01SIM prefix for easy identification
USER_IDS = [
    "01SIMAAAAAAAAAAAAAAAAAAAAAA",
    "01SIMBBBBBBBBBBBBBBBBBBBBB",
    "01SIMCCCCCCCCCCCCCCCCCCCCC",
    "01SIMDDDDDDDDDDDDDDDDDDDDD",
    "01SIMEEEEEEEEEEEEEEEEEEEEE",
    "01SIMFFFFFFFFFFFFFFFFFFFFFFA",
    "01SIMGGGGGGGGGGGGGGGGGGGGGG",
    "01SIMHHHHHHHHHHHHHHHHHHHHHH",
    "01SIMIIIIIIIIIIIIIIIIIIIIII",
    "01SIMJJJJJJJJJJJJJJJJJJJJJJ",
    "01SIMKKKKKKKKKKKKKKKKKKKKKK",
    "01SIMLLLLLLLLLLLLLLLLLLLLLL",
    "01SIMMMMMMMMMMMMMMMMMMMMMMM",
    "01SIMNNNNNNNNNNNNNNNNNNNNNN",
    "01SIMOOOOOOOOOOOOOOOOOOOOOO",
    "01SIMPPPPPPPPPPPPPPPPPPPPPP",
    "01SIMQQQQQQQQQQQQQQQQQQQQQQ",
    "01SIMRRRRRRRRRRRRRRRRRRRRRR",
    "01SIMSSSSSSSSSSSSSSSSSSSSSS",
    "01SIMTTTTTTTTTTTTTTTTTTTTTT",
]


def random_message() -> str:
    return random.choice(MESSAGES)


def random_emoji() -> str:
    return random.choice(EMOJI_REACTIONS)


def get_user_spec(index: int) -> tuple[str, str, str]:
    """Return (user_id, username, display_name) for user at index."""
    user_id = USER_IDS[index % len(USER_IDS)]
    username, display_name = USER_POOL[index % len(USER_POOL)]
    return user_id, username, display_name
