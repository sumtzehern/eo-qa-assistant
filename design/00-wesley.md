
# Additional consideration by Wesley

1. Embedding are built for scale
- batch jobs for new question (queue-base)
- dsitributed vector DB
- hybrid search (BM25 + dense)
- Sharding by product/ issue type
- store meta data alongside vector

2. Retrieval + generation (tight path)
- Keep the path fast and lean
- query -> metadata filter -> cache -> hybrid search -> rerank -> LLM
- most queries hit cache, many never reach vector search
- rerank small candidates sets only
- send 5-10 HIGH Quality chunk
- More data not always bettter answer, but RELEVENCE wins

3. Caching is everything
- FAQ cache (repeat question)
- Retrieval cache (top question cluster)
- Embedding cache (hot queries)

flow: Query -> cache -> (miss) retrive + LLM + store result

4. Monitor + Eval
- Are we retrieving the right document or source,
- Are the answer actually helpful
- latency + cache hit rate
- auto re-embed as new question/ tickets comes in.