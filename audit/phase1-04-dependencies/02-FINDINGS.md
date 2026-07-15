# Findings Report - Dependencies & Security

**Audit Phase:** Phase 4: Dependencies & Security
**Date:** 2026-07-09
**Status:** IN PROGRESS

---

## Critical Findings

| ID | Finding | Location | Severity | CVSS | Status |
|----|---------|----------|----------|------|--------|
| DEP-001 | Hardcoded API key in test file | `tests/test_nvidia_nim_client.py:70` | MEDIUM | - | OPEN |

## High Findings

| ID | Finding | Location | Severity | CVSS | Status |
|----|---------|----------|----------|------|--------|
| DEP-002 | pip-audit not yet executed | environment | HIGH | - | OPEN |
| DEP-003 | npm audit not yet executed | dashboard/ | HIGH | - | OPEN |
| DEP-004 | Docker image scan not performed | Docker | HIGH | - | OPEN |

## Medium Findings

| ID | Finding | Location | Priority | Status |
|----|---------|----------|----------|--------|
| MCP-001 | Missing version constraints for some packages | `requirements.txt` | MEDIUM | OK |
| MCP-002 | Kafka-python-ng without version pin | `requirements.txt` | LOW | OK |

## Low Findings

| ID | Finding | Location | Priority | Status |
|----|---------|----------|----------|--------|
| LOP-001 | No Dagster version specified (commented) | `requirements.txt` | LOW | OK |

## Observations (No Action Required)

| ID | Observation | Notes |
|----|-------------|-------|
| OBS-001 | Requirements.txt uses minimum version constraints (`>=`) | This allows security updates but may cause compatibility issues |
| OBS-002 | No direct boto3dependency | AWS integrations may use indirect dependencies |
| OBS-003 | .env.example properly documented | All required secrets documented |
| OBS-004 | API keys properly loaded from config | `config.get("api_key")` pattern used |

---

## Secret Scan Results

### Hardcoded Passwords
```bash
# Checked: grep -rn "password\s*=" --include="*.py"
agents/alert_dispatcher_agent.py:385:        smtp_password = config.get("smtp_password")
scripts/alert_consumer.py:137:    smtp_password = config.get("smtp_password")
```
**Status:** OK - These are config lookups, not hardcoded values

### API Keys
```bash
# Checked: grep -rn "api_key\s*=" --include="*.py"
collectors/crunchbase.py:60:        api_key = api_config.get("api_key", "")
```
**Status:** OK - Loaded from configuration

### Test File Anomaly (DEP-001)
```python
# tests/test_nvidia_nim_client.py:70
api_key = "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"
```
**Concern:** Test files should use mock/fake values, not format-like API keys
**Action:** Verify this is not a real NVIDIA API key before proceeding

### OpenAI-style Keys
```bash
# grep for "sk-" patterns
(none found in production code)
```

---

## Vulnerability Assessment

### Python Packages
- **pymysql >=1.1.0** - Major security updates in 1.1.0+
- **requests >=2.31.0** - Good version constraint
- **fastapi >=0.110.0** - Newer version, includes security patches
- **bcrypt >=4.1.0** - Good version for password hashing

### Missing Audit Tools
- [ ] pip-audit needs execution
- [ ] npm audit needs execution in dashboard/
- [ ] Docker security scan needs execution

---

## Next Steps

1. [ ] Run pip-audit in virtual environment
2. [ ] Run npm audit in dashboard/
3. [ ] Verify NVIDIA API key in test file is not real
4. [ ] Run Docker security scan
5. [ ] Check for outdated package versions

---

**Total Findings:** 4
**Critical:** 0 | **High:** 3 | **Medium:** 2 | **Low:** 1

**Auditor:** Claude Code Agent  
**Date:** 2026-07-09