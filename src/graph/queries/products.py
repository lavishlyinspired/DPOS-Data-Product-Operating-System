GET_BY_ID = "MATCH (p:DataProduct {id: $id}) RETURN p"
CREATE = "MATCH (d:Domain {id: $did}) MERGE (p:DataProduct {id: $id}) SET p += $props MERGE (p)-[:IN_DOMAIN]->(d)"
LINK_SCHEMA = "MATCH (p:DataProduct {id: $pid}), (s:Schema {id: $sid}) MERGE (p)-[:HAS_SCHEMA]->(s)"