from typing import List, Dict, Any
from src.graph.manager import Neo4jManager


class PolicyResolver:
    def __init__(self):
        self.manager = Neo4jManager()

    # ------------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------------

    def resolve_policies(
        self,
        product_id: str,
        base_rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge contract rules with applicable policies.
        Precedence: GLOBAL → DOMAIN → PRODUCT
        """
        policies = (
            self._fetch_global_policies()
            + self._fetch_domain_policies(product_id)
            + self._fetch_product_policies(product_id)
        )

        # sort by priority (low → high)
        policies.sort(key=lambda p: p.get("priority", 0))

        rules_map = {r["id"]: r for r in base_rules}

        for policy in policies:
            for pr in policy.get("rules", []):
                target_rule_id = pr.get("target_rule_id")

                if target_rule_id and target_rule_id in rules_map:
                    matches = [rules_map[target_rule_id]]
                else:
                    matches = [
                        r for r in rules_map.values()
                        if r["type"] == pr.get("type")
                        and r.get("field") == pr.get("field")
                    ]

                for rule in matches:
                    for k, v in pr.items():
                        if k.endswith("_override") and v is not None:
                            rule[k.replace("_override", "")] = v

        return list(rules_map.values())

    # ------------------------------------------------------------------
    # FETCHERS (NO AGGREGATION TRICKS)
    # ------------------------------------------------------------------

    def _fetch_global_policies(self) -> List[Dict]:
        query = """
        MATCH (p:Policy {scope:'GLOBAL', is_active:true})
        OPTIONAL MATCH (p)-[:HAS_POLICY_RULE]->(r:PolicyRule)
        WITH p, collect(DISTINCT r) AS rules
        RETURN {
            id: p.id,
            priority: coalesce(p.priority, 0),
            scope: 'GLOBAL',
            rules: rules
        } AS policy
        """
        result = self.manager.execute_query(query)
        return [r["policy"] for r in result] if result else []

    def _fetch_domain_policies(self, product_id: str) -> List[Dict]:
        query = """
        MATCH (prod:DataProduct {id:$id})-[:IN_DOMAIN]->(d:Domain)
        MATCH (p:Policy {scope:'DOMAIN', is_active:true})-[:APPLIES_TO_DOMAIN]->(d)
        OPTIONAL MATCH (p)-[:HAS_POLICY_RULE]->(r:PolicyRule)
        WITH p, collect(DISTINCT r) AS rules
        RETURN {
            id: p.id,
            priority: coalesce(p.priority, 0),
            scope: 'DOMAIN',
            rules: rules
        } AS policy
        """
        result = self.manager.execute_query(query, {"id": product_id})
        return [r["policy"] for r in result] if result else []

    def _fetch_product_policies(self, product_id: str) -> List[Dict]:
        query = """
        MATCH (p:Policy {scope:'PRODUCT', is_active:true})
              -[:APPLIES_TO_PRODUCT]->(:DataProduct {id:$id})
        OPTIONAL MATCH (p)-[:HAS_POLICY_RULE]->(r:PolicyRule)
        WITH p, collect(DISTINCT r) AS rules
        RETURN {
            id: p.id,
            priority: coalesce(p.priority, 0),
            scope: 'PRODUCT',
            rules: rules
        } AS policy
        """
        result = self.manager.execute_query(query, {"id": product_id})
        return [r["policy"] for r in result] if result else []
