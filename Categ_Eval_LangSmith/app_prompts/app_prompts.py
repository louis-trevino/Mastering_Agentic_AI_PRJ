CATEG_PROMPT_WEAK = """Act like a customer support agent who can classify a user request into the best category.

Classify the customer's ticket into EXACTLY ONE of these categories:

- order_status: questions about customer order
- refund_request: the customer wants their money back
- product_issue: the delivered product has a problem
- account_help: help with the user's account info
- other: anything that doesn't fit the above

Return only the category key.

Ticket:
{ticket_text}
"""


CATEG_PROMPT = """Act like a customer support agent who can classify a user request into the best category.

Classify the customer's ticket into EXACTLY ONE of these categories:

- order_status: questions about where an order is, tracking, delivery ETA
- refund_request: the customer wants their money back
- product_issue: the item arrived broken, wrong, defective, or not as described
- account_help: login, password, address, payment method changes
- other: anything that doesn't fit the above (general questions, feedback, browsing)

Return only the category key.

Ticket:
{ticket_text}
"""




CATEG_PROMPT_STRONG = """Act like a customer support agent who can classify a user request into the best category.

Classify the customer's ticket into EXACTLY ONE of these categories:

- order_status: questions about where an order is, tracking, delivery ETA, or non-delivery
- refund_request: the customer is asking for their money back (and the item itself is fine, or already returned)
- product_issue: the item arrived broken, wrong, defective, or not as described — even if the customer also asks for a refund as the remedy
- account_help: login, password, address, or payment method changes
- other: general questions, feedback, browsing, anything not covered above

Disambiguation rules:
1. If a damaged/wrong/defective item is mentioned, the category is product_issue — regardless of what remedy the customer asks for.
2. If the customer never received the order, the category is order_status — even if they mention wanting their money back.
3. If the customer is asking about a refund they already initiated ("where is my refund?"), the category is refund_request.
4. Site bugs that prevent checkout are account_help.

Think step by step:
1. What is the customer's *primary* problem? (one sentence)
2. Which category fits that problem best?

Ticket:
{ticket_text}
"""

