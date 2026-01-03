CREATE = "MATCH (p:DataProduct {id: $pid}) MERGE (c:Contract {id: $id}) SET c += $props MERGE (p)-[:HAS_CONTRACT]->(c)"
CREATE_RULE = "MATCH (c:Contract {id: $cid}) MERGE (r:Rule {id: $id}) SET r += $props MERGE (c)-[:HAS_RULE]->(r)"
GET_RULES = "MATCH (p:DataProduct {id: $id})-[:HAS_CONTRACT]->(c)-[:HAS_RULE]->(r) RETURN r"