# Unknown Register

| ID | Unknown | Impact | Handling |
|---|---|---|---|
| U-GRAPHITI-API | Exact live Graphiti client API/version in target runtime | Direct live ingestion adapter may need a thin sink implementation | Default sink is deterministic local report; Graphiti sink remains an extension point |
| U-V2-INDEX-FINAL | Final production shape of V2 retrieval/index output | Field mapping may require additional aliases | Exporter supports common aliases and fails closed on missing required fields |
| U-DEPLOY-SECRETS | Neo4j/Graphiti credentials and endpoints | Cannot wire production push | No credentials are invented; use environment/runtime config |
