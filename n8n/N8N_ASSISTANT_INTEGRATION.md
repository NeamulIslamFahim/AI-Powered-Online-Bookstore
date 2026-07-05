# n8n Assistant Integration

This project sends assistant webhook requests to `N8N_CHAT_WEBHOOK_URL` for informational assistant replies.

## Incoming Request Shape

The backend sends JSON like this:

```json
{
  "chatInput": "show reviews for Atomic Habits",
  "sessionId": "assistant_123",
  "temperature": 0.5,
  "intentHint": "reviews",
  "state": "book_selected",
  "timestamp": "2026-04-08T10:00:00Z",
  "user": {
    "id": 1,
    "name": "Fahim",
    "email": "fahim@example.com",
    "role": "customer"
  },
  "selectedBook": {
    "id": 2,
    "title": "Atomic Habits",
    "author": "James Clear",
    "description": "A practical guide to building habits and breaking unhelpful patterns.",
    "price": 18.0,
    "stock_quantity": 35
  }
}
```

## Required Response Shape

Return JSON with one of these top-level fields:

```json
{
  "reply": "Atomic Habits is rated 4.7/5 by readers. Many readers praise its practical advice and easy structure."
}
```

Also accepted:

```json
{
  "message": "Your reply text here"
}
```

or

```json
{
  "output": "Your reply text here"
}
```

Optional token usage:

```json
{
  "reply": "Your reply text here",
  "tokenUsage": {
    "input": 210,
    "output": 92,
    "total": 302
  }
}
```

## Recommended n8n Logic

Use the incoming fields like this:

- `{{$json.chatInput}}` as the user message
- `{{$json.temperature || 0.5}}` as the model temperature
- `{{$json.intentHint}}` to steer the prompt
- `{{$json.selectedBook}}` for title, price, author, and stock context

Keep these behaviors:

- For `reviews`, answer review or opinion questions.
- For `browse`, recommend or list books.
- For `general`, answer conversational book questions.
- Do not perform final order placement in n8n. The app backend still handles checkout and order creation.

## Example Code Node Output

If you use an n8n Code node before the final Webhook Response node, this is a simple safe format:

```javascript
const chatInput = $json.chatInput ?? "";
const book = $json.selectedBook?.title;
const price = $json.selectedBook?.price;
const intent = $json.intentHint ?? "general";

let reply = "I can help with books, reviews, and pricing.";

if (intent === "reviews" && book) {
  reply = `${book} has positive reader feedback overall. If you want, I can also help compare it with similar books.`;
} else if (intent === "browse" && book) {
  reply = `${book} is available for $${price}. You can also ask me for reviews or similar recommendations.`;
} else if (book) {
  reply = `${book} is currently priced at $${price}. You can ask for reviews, negotiate, or continue with the order in the app.`;
}

return [
  {
    json: {
      reply,
      tokenUsage: {
        input: 0,
        output: 0,
        total: 0
      }
    }
  }
];
```

## Webhook Response Node

Your last n8n node should return the JSON object directly, for example:

```json
{
  "reply": "Atomic Habits is available for $18.00. Readers generally like its practical advice and clarity."
}
```

If n8n returns a different shape, this app will ignore it and fall back to local assistant logic.
