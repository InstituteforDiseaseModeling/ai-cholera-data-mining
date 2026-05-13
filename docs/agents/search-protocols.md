# Search Protocols and Query Strategies

## Multi-Engine Search Requirements

Use a minimum of 15 distinct search engines/databases per country:
- Google, Google Scholar
- PubMed, PubMed Central
- WHO databases, WHO AFRO
- ReliefWeb, OCHA
- Government health ministry websites
- Academic institutional repositories
- News aggregators (regional/local)
- ProMED-mail archives
- UNICEF data platforms
- MSF/Doctors Without Borders reports

## Query Categories (All Mandatory)

### 1. WHO/Official Queries
- "{Country} cholera surveillance WHO {year}"
- "{Country} ministry health cholera bulletin {period}"
- "{Country} epidemiological report cholera {gap_dates}"

### 2. Academic/Research Queries
- "{Country} cholera phylogenetic analysis {years}"
- "{Country} cholera epidemiology study {period}"
- "site:{academic_domain} {Country} cholera {gap_years}"

### 3. Humanitarian/NGO Queries
- "{Country} UNICEF cholera response {period}"
- "{Country} MSF cholera treatment {dates}"
- "{Country} OCHA humanitarian cholera {year}"

### 4. Regional/Cross-border Queries
- "{Country} {neighbor} cholera cross-border {period}"
- "{Region} cholera outbreak {Country} {dates}"
- "{Country} cholera refugee camp {border_area}"

### 5. Historical/Archive Queries
- "{Country} cholera colonial records {decade}"
- "site:archive.org {Country} cholera {historical_period}"
- "{Country} cholera missionary reports {years}"

### 6. Technical/Laboratory Queries
- "{Country} cholera laboratory confirmation {period}"
- "{Country} Vibrio cholerae isolation {dates}"
- "{Country} cholera diagnostic capacity {year}"

### 7. Local Language Queries
- Use vernacular terms for cholera
- Local spellings of place names
- Regional media in local languages

## Advanced Search Techniques

### Temporal Granularity
- Search by month: "January 2019", "February 2019"
- Search by season: "rainy season 2020", "dry season 2021"
- Search by decade: "1990s", "2000s", "2010s"

### Geographic Granularity
- National: "{Country} cholera"
- Provincial: "{Province} cholera"
- District: "{District} cholera outbreak"
- Municipal: "{City} cholera cases"

### Source Chain Following
1. Find initial source
2. Check all references/citations
3. Search for cited authors' other work
4. Look for updated versions
5. Find related institutional reports

### Alternative Access Methods
- Use Google Cache for broken links
- Try Internet Archive Wayback Machine
- Search for PDF filename directly
- Contact authors/institutions
- Check institutional repositories

## Batch Execution Requirements

### Parallel Processing (Mandatory)
```python
# Execute 20 queries simultaneously
batch = [
    WebSearch("Angola cholera WHO 2019"),
    WebSearch("Angola cholera UNICEF 2019"),
    WebSearch("Angola cholera MSF 2019"),
    # ... 17 more queries
]
```

### Query Distribution per Batch
- 5-6 institutional queries (WHO, MoH)
- 4-5 humanitarian queries (UNICEF, NGOs)
- 4-5 academic queries
- 3-4 news/media queries
- 2-3 specialized queries

## Performance Tracking

Document in search logs:
- Batch number and timestamp
- Queries executed
- Sources discovered
- Data observations added
- Yield percentage
- Time elapsed