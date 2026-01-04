# COVID-19 Demo Data (Synthetic)

This folder contains synthetic CSVs used by the DPOS walkthrough notebook.

Design goals:
- Business-themed for a COVID-19 outreach scenario
- Same schema as the existing `data/good/customers.csv` and `data/bad/customers_bad.csv`
  so existing contracts/rules for product `DP001` can validate/enforce without
  changing the graph model.

Files:
- `good/outreach_list.csv`: clean records (contactable, valid segment, valid timestamps)
- `bad/outreach_list_bad.csv`: intentionally flawed records to trigger validation failures
