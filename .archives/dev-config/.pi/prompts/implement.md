Implement a new feature: {{description=the feature to implement}}

Follow the compound engineering loop:
1. Read relevant skills (kg_search for patterns)
2. Implement ONE feature, validate manually, write 5 tests
3. Wire into compound executor or appropriate layer at creation time
4. FLUME-First: encode/decode through FLUME if it's a new module
5. Run `make validate` to verify compound loop integrity
6. Commit with conventional commit format