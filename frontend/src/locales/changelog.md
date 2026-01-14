## June + July 2025

- added connection to postgresql database
- embeddings are now stored in a postgresql db
- knowledge graph for domain knowledge stored in postgresql db
- now using hosted embedding model "qwen-3-embedding-4b"
- evaluated and implemented various ingesting/retrieving strategies
- set up python to work with uv instead of pip for faster and cleaner dependency resolving

## 23.04.2025

- LLMs are represented as their features now, instead of the specific names
- Added more inspirations for Free Chat
- Fixed a bug where locale was changed back to the default at random times

## 22.04.2025

- Added additional books for all topics
- Added Multi Query Retriever to SC-Bot (toggleable through admin view)

## 31.03.2025

- Retry of messages possible
- Added Learning Strategies module
- Fixed bug where curly braces were breaking chats
- Updated to newest version of ST-Buddy
- Updated prompt formatting

## 12.02.2025

- rename learning type to learning style
- summarize long conversations
- retry responses
- new logo/icon

## 05.02.2025

- display progress while waiting on a message ('searching in sources xyz', 'generating message using sources xyz / using model zyx')
- more natural flow of displaying incoming message stream (small delay between displaying new text chunks, speeding up when full message was received)
- reintroduced timestamps on chat messages
- Fixed a bug where curly braces in user messages would cause errors during processing

## 04.02.2025

- ability to adjust learning goals manually
- "Novice" skill level was introduced to represent user who has no knowledge
- added new logo and icon/favicon
- increased compatibility with DeepSeek R1 (saving thoughts when no `<think>` was received)

## 03.02.2025

- streaming of messages enabled via chat settings (gear icon)
- look of the chat window was improved

## 30.01.2025

- Improved font styles over the whole UI
