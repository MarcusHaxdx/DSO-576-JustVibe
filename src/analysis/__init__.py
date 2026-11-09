"""Analysis backend for the DQC review dashboard.

Layers (each file has one job, none reads another layer's internals):
  loader   read + validate the clean CSV          -> DataFrame
  filters  apply a FilterSpec                     -> DataFrame
  metrics  pure functions for M1-M4               -> DataFrame / dict
  triage   rule-based review ranking (M5)         -> DataFrame
  runs     optional agent-run scoring (M6)        -> DataFrame
"""
