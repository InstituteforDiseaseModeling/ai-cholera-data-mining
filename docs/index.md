# AI Cholera Surveillance Documentation Index

## Quick Links
- [Quick Start Guide](quick-start.md) - Get started in 5 minutes
- [Agent Workflow Overview](agents/workflow-overview.md) - Understand the 6-agent system
- [Data Standards](technical/data-standards.md) - File formats and specifications

## Documentation by Role

### For AI Agents
- [Workflow Overview](agents/workflow-overview.md) - 6-agent system guide
- [Gap-Targeted Search](agents/gap-targeting.md) - Methodology for finding missing data
- [Search Protocols](agents/search-protocols.md) - Query strategies and templates
- [Stopping Criteria](agents/stopping-criteria.md) - When to conclude searches

### For Developers
- [Data Standards](technical/data-standards.md) - Column definitions and formats
- [Quality Control](technical/quality-control.md) - Validation protocols
- [Dashboard System](technical/dashboard-system.md) - Automated tracking
- [API Reference](technical/api-reference.md) - File formats and interfaces

### For Data Scientists
- [Gap Analysis](methodology/gap-analysis.md) - Scientific approach to surveillance gaps
- [Zero-Transmission](methodology/zero-transmission.md) - Documenting absence periods
- [Source Hierarchy](methodology/source-hierarchy.md) - Evidence level framework
- [MOSAIC Integration](methodology/mosaic-integration.md) - Modeling framework

### For Project Managers
- [Country Prioritization](operations/country-prioritization.md) - MOSAIC framework
- [Access Permissions](operations/access-permissions.md) - Domain authorizations
- [Pilot Lessons](operations/pilot-lessons.md) - Angola case study insights
- [Troubleshooting](operations/troubleshooting.md) - Common issues and solutions

## Templates & Examples
- [Code Examples](../templates/code-examples/) - Python snippets
- [Query Templates](../templates/query-templates/) - Search query patterns
- [Workflow Examples](../templates/workflow-examples/) - Implementation guides

## Reference Materials
- [Checklists](../reference/checklists/) - Quality assurance checklists
- [Decision Trees](../reference/decision-trees/) - Workflow decision guides

## Key Files & Commands

### Essential Reference Files
| File | Purpose |
|------|---------|
| `reference/agent_quick_reference.csv` | Country priorities and gaps |
| `reference/comprehensive_gaps_inventory.csv` | All gaps ≥7 days |
| `reference/priority_sources.txt` | 486 authorized domains |

### Common Commands
```bash
# Generate orchestrator
python py/generate_country_orchestrator.py {ISO}

# Update dashboard
bash update_dashboard.sh

# Analyze gaps
python py/analyze_integrated_coverage_gaps.py
```

## Support

For additional help:
1. Check relevant documentation section above
2. Review templates and examples
3. Consult pilot lessons learned
4. Follow troubleshooting guide