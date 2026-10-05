"""The fixed replies for declined questions (AST-002 design "The fixed replies").

Written by us, not by the model, so they are identical every time and cannot be argued out of
their wording. In-app links only. None of them repeats any text from the question.
"""

from app.assistant.guard import DECLINED, Intent

HELP = """\
I can help with:

- **Your invoices**: who owes what, what is overdue or due soon, and what has been paid.
- **Your contracts**: parties, key dates, terms and risks.
- **This app**: what it does and how to use it.

For example, you could ask: “Which invoices are unpaid as of today?”, “What risks are in my \
contracts?” or “How does this app work?”\
"""

_GENERAL = (
    "I can only help with your contracts and invoices, and with explaining how this app works, "
    "so I can't help with that.\n\n" + HELP
)

_WRITE = (
    "I can only look things up, so I can't change anything or send anything for you.\n\n"
    "- To record a payment or fix an invoice, upload your updated spreadsheet on the "
    "[Upload invoices](/invoices/upload) page.\n"
    "- To remind a client about an overdue invoice, use the **Send email reminder** button on "
    "the [overdue invoices](/invoices?view=outstanding) list.\n\n" + HELP
)

_LEGAL = (
    "I can explain what your contracts say, but I can't give legal advice or tell you what to do "
    "legally. For that, please speak to a lawyer or adviser.\n\n" + HELP
)

REPLIES: dict[Intent, str] = {
    Intent.OFF_TOPIC: _GENERAL,
    Intent.MANIPULATION: _GENERAL,
    Intent.WRITE_REQUEST: _WRITE,
    Intent.LEGAL_ADVICE: _LEGAL,
}
assert set(REPLIES) == DECLINED  # every declined intent has a reply


def reply_for(intent: Intent) -> str:
    return REPLIES[intent]
