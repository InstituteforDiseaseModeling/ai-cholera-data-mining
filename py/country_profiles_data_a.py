"""
Country profile source data, part A (AGO-LBR).

Per-country search-targeting data for the 20 first MOSAIC framework countries.
Consumed by py/build_country_profiles.py, which merges part A + part B and
emits ./reference/country_profiles.json.

Field notes:
  adm1                  First-level administrative units (provinces/regions/
                        states/counties). Used by Agent 2 for geographic
                        expansion queries. Names are official English or
                        official-language forms as used in national reporting.
  major_cities          Urban centres that appear in outbreak reporting.
  neighbors             Land-bordering countries (ISO3). Used for cross-border
                        and regional-context queries.
  search_languages      ISO 639-1 codes to search in, most productive first.
  disease_terms         Localized search terms for "cholera" / "acute watery
                        diarrhoea", for non-English query construction.
  health_domains        Candidate ministry-of-health / NPHI domains. UNVERIFIED
                        at authoring time - py/verify_country_profiles.py
                        URL-checks these and records status in the emitted JSON.
  season                Free-text cholera seasonality for seasonal query context.
"""

PROFILES_A = {
    "AGO": {
        "name": "Angola", "iso2": "AO", "subregion": "Central Africa",
        "adm1": ["Bengo", "Benguela", "Bie", "Cabinda", "Cuando", "Cubango",
                 "Cuanza Norte", "Cuanza Sul", "Cunene", "Huambo", "Huila",
                 "Icolo e Bengo", "Luanda", "Lunda Norte", "Lunda Sul", "Malanje",
                 "Moxico", "Moxico Leste", "Namibe", "Uige", "Zaire"],
        "adm1_legacy": {
            # Law of 5 Sep 2024 split Cuando Cubango into Cuando + Cubango,
            # carved Icolo e Bengo out of Luanda and Moxico Leste out of Moxico.
            # Every pre-2025 Angolan record uses the 18-province names.
            "pre_2025": ["Bengo", "Benguela", "Bie", "Cabinda", "Cuando Cubango",
                         "Cuanza Norte", "Cuanza Sul", "Cunene", "Huambo", "Huila",
                         "Luanda", "Lunda Norte", "Lunda Sul", "Malanje", "Moxico",
                         "Namibe", "Uige", "Zaire"],
        },
        "major_cities": ["Luanda", "Huambo", "Lobito", "Benguela", "Lubango", "Cabinda", "Malanje"],
        "neighbors": ["COD", "COG", "ZMB", "NAM"],
        "search_languages": ["pt", "en"],
        "disease_terms": ["colera", "diarreia aguda aquosa", "surto de colera"],
        "health_domains": ["minsa.gov.ao", "inis.gov.ao"],
        "season": "Rainy season Oct-Apr; Luanda peri-urban outbreaks; 2006 and 2025 major epidemics",
    },
    "BDI": {
        "name": "Burundi", "iso2": "BI", "subregion": "East Africa",
        "adm1": ["Buhumuza", "Bujumbura", "Burunga", "Butanyerera", "Gitega"],
        "adm1_legacy": {
            # Merged to 5 provinces at the 2025 legislative elections (2023 reform
            # law). All historical cholera reporting uses the 18.
            "pre_2025": ["Bubanza", "Bujumbura Mairie", "Bujumbura Rural", "Bururi",
                         "Cankuzo", "Cibitoke", "Gitega", "Karuzi", "Kayanza",
                         "Kirundo", "Makamba", "Muramvya", "Muyinga", "Mwaro",
                         "Ngozi", "Rumonge", "Rutana", "Ruyigi"],
        },
        "major_cities": ["Bujumbura", "Gitega", "Ngozi", "Rumonge", "Muyinga"],
        "neighbors": ["COD", "RWA", "TZA"],
        "search_languages": ["fr", "en"],
        "disease_terms": ["cholera", "diarrhee aqueuse aigue", "epidemie de cholera"],
        "health_domains": ["minisante.bi"],
        "season": "Lake Tanganyika shoreline endemic focus; rainy seasons Feb-May and Sep-Dec",
    },
    "BEN": {
        "name": "Benin", "iso2": "BJ", "subregion": "West Africa",
        "adm1": ["Alibori", "Atacora", "Atlantique", "Borgou", "Collines", "Couffo",
                 "Donga", "Littoral", "Mono", "Oueme", "Plateau", "Zou"],
        "major_cities": ["Cotonou", "Porto-Novo", "Parakou", "Abomey-Calavi", "Djougou"],
        "neighbors": ["BFA", "NER", "NGA", "TGO"],
        "search_languages": ["fr", "en"],
        "disease_terms": ["cholera", "diarrhee aqueuse aigue", "epidemie de cholera"],
        "health_domains": ["sante.gouv.bj"],
        "season": ("Coastal lagoon foci (Cotonou, Oueme delta, So-Ava, Abomey-Calavi); "
                   "primary rains Apr-Jul, but outbreaks cluster in the Aug-Nov "
                   "secondary window"),
    },
    "BFA": {
        "name": "Burkina Faso", "iso2": "BF", "subregion": "West Africa",
        "adm1": ["Bankui", "Djoro", "Goulmou", "Guiriko", "Kadiogo", "Kuilse",
                 "Liptako", "Nakambe", "Nando", "Nazinon", "Oubri", "Sirba",
                 "Soum", "Sourou", "Tannounyan", "Tapoa", "Yaadga"],
        "adm1_legacy": {
            # Renamed to endogenous toponyms on 2 July 2025. The 13 directional
            # French names cover 1970-2025, i.e. nearly all existing data.
            "pre_2025": ["Boucle du Mouhoun", "Cascades", "Centre", "Centre-Est",
                         "Centre-Nord", "Centre-Ouest", "Centre-Sud", "Est",
                         "Hauts-Bassins", "Nord", "Plateau-Central", "Sahel",
                         "Sud-Ouest"],
        },
        "major_cities": ["Ouagadougou", "Bobo-Dioulasso", "Koudougou", "Ouahigouya", "Banfora"],
        "neighbors": ["BEN", "CIV", "GHA", "MLI", "NER", "TGO"],
        "search_languages": ["fr", "en"],
        "disease_terms": ["cholera", "diarrhee aqueuse aigue"],
        "health_domains": ["sante.gov.bf"],
        "season": "Rainy season Jun-Sep; displacement-linked risk in Sahel and Centre-Nord",
    },
    "BWA": {
        "name": "Botswana", "iso2": "BW", "subregion": "Southern Africa",
        "adm1": ["Central", "Chobe", "Ghanzi", "Kgalagadi", "Kgatleng", "Kweneng",
                 "North East", "North West", "South East", "Southern", "Gaborone",
                 "Francistown", "Lobatse", "Selebi-Phikwe", "Jwaneng", "Sowa"],
        "major_cities": ["Gaborone", "Francistown", "Maun", "Kasane", "Serowe"],
        "neighbors": ["NAM", "ZAF", "ZWE", "ZMB"],
        "search_languages": ["en"],
        "disease_terms": ["cholera", "acute watery diarrhoea"],
        "health_domains": ["www.moh.gov.bw"],
        "season": "Rare; importation risk via Zimbabwe/Zambia borders (Chobe, North East)",
    },
    "CAF": {
        "name": "Central African Republic", "iso2": "CF", "subregion": "Central Africa",
        "adm1": ["Bamingui-Bangoran", "Bangui", "Basse-Kotto", "Haut-Mbomou", "Haute-Kotto",
                 "Kemo", "Lobaye", "Mambere-Kadei", "Mbomou", "Nana-Grebizi",
                 "Nana-Mambere", "Ombella-M'Poko", "Ouaka", "Ouham", "Ouham-Pende",
                 "Sangha-Mbaere", "Vakaga"],
        "major_cities": ["Bangui", "Bimbo", "Berberati", "Bambari", "Bangassou", "Mobaye"],
        "neighbors": ["CMR", "TCD", "SDN", "SSD", "COD", "COG"],
        "search_languages": ["fr", "en"],
        "disease_terms": ["cholera", "diarrhee aqueuse aigue"],
        "health_domains": ["sante-rca.org", "sante.gouv.cf"],
        "season": "Ubangi river corridor (Bangui, Mobaye, Basse-Kotto); conflict-disrupted surveillance",
    },
    "CIV": {
        "name": "Cote d'Ivoire", "iso2": "CI", "subregion": "West Africa",
        "adm1": ["Abidjan", "Bas-Sassandra", "Comoe", "Denguele", "Goh-Djiboua", "Lacs",
                 "Lagunes", "Montagnes", "Sassandra-Marahoue", "Savanes",
                 "Vallee du Bandama", "Woroba", "Yamoussoukro", "Zanzan"],
        "major_cities": ["Abidjan", "Bouake", "Yamoussoukro", "San-Pedro", "Korhogo", "Daloa"],
        "neighbors": ["BFA", "GHA", "GIN", "LBR", "MLI"],
        "search_languages": ["fr", "en"],
        "disease_terms": ["cholera", "diarrhee aqueuse aigue"],
        "health_domains": ["sante.gouv.ci"],
        "season": "Abidjan lagoon precarious settlements; rainy season May-Jul",
    },
    "CMR": {
        "name": "Cameroon", "iso2": "CM", "subregion": "Central Africa",
        "adm1": ["Adamawa", "Centre", "East", "Far North", "Littoral", "North",
                 "North-West", "South", "South-West", "West"],
        "major_cities": ["Douala", "Yaounde", "Garoua", "Bamenda", "Maroua", "Bafoussam", "Kousseri"],
        "neighbors": ["NGA", "TCD", "CAF", "COG", "GAB", "GNQ"],
        "search_languages": ["fr", "en"],
        "disease_terms": ["cholera", "diarrhee aqueuse aigue"],
        "health_domains": ["minsante.cm"],
        "season": ("South-West (Bakassi peninsula, Ekondo Titi, Bamusso) and "
                   "Littoral/Douala dominated the 2021-23 epidemic, the largest recent "
                   "event - Far North had almost no cases in it. Far North "
                   "(Logone/Chari, Lake Chad basin) is the HISTORICAL pre-2020 focus. "
                   "Dual French/English reporting."),
    },
    "COD": {
        "name": "Democratic Republic of Congo", "iso2": "CD", "subregion": "Central Africa",
        "adm1": ["Bas-Uele", "Equateur", "Haut-Katanga", "Haut-Lomami", "Haut-Uele", "Ituri",
                 "Kasai", "Kasai-Central", "Kasai-Oriental", "Kinshasa", "Kongo-Central",
                 "Kwango", "Kwilu", "Lomami", "Lualaba", "Mai-Ndombe", "Maniema", "Mongala",
                 "Nord-Kivu", "Nord-Ubangi", "Sankuru", "Sud-Kivu", "Sud-Ubangi",
                 "Tanganyika", "Tshopo", "Tshuapa"],
        "adm1_legacy": {
            # Laws 015/004 and 015/006 of 2015 split 11 provinces into 26. DRC
            # carries the highest cholera burden of the 40, and ALL pre-2015
            # reporting uses these names - notably Katanga, which became
            # Haut-Katanga/Haut-Lomami/Lualaba/Tanganyika, and Tanganyika
            # (Kalemie) is a flagship endemic focus.
            "pre_2015": ["Katanga", "Orientale", "Bandundu", "Bas-Congo",
                         "Equateur", "Kasai-Occidental", "Kasai-Oriental",
                         "Kinshasa", "Maniema", "Nord-Kivu", "Sud-Kivu"],
        },
        "major_cities": ["Kinshasa", "Lubumbashi", "Goma", "Bukavu", "Kisangani", "Kalemie",
                         "Uvira", "Mbandaka", "Kananga"],
        "neighbors": ["AGO", "BDI", "CAF", "COG", "RWA", "SSD", "TZA", "UGA", "ZMB"],
        "search_languages": ["fr", "en"],
        "disease_terms": ["cholera", "diarrhee aqueuse aigue", "epidemie de cholera"],
        "health_domains": ["sante.gouv.cd", "www.insp.cd"],
        "season": "Endemic Great Lakes foci (Sud-Kivu/Uvira, Nord-Kivu, Tanganyika); epidemic spread along Congo river to Kinshasa",
    },
    "COG": {
        "name": "Republic of the Congo", "iso2": "CG", "subregion": "Central Africa",
        "adm1": ["Bouenza", "Brazzaville", "Cuvette", "Cuvette-Ouest", "Kouilou", "Lekoumou",
                 "Likouala", "Niari", "Plateaux", "Pointe-Noire", "Pool", "Sangha"],
        "major_cities": ["Brazzaville", "Pointe-Noire", "Dolisie", "Ouesso", "Impfondo"],
        "neighbors": ["AGO", "CMR", "CAF", "COD", "GAB"],
        "search_languages": ["fr", "en"],
        "disease_terms": ["cholera", "diarrhee aqueuse aigue"],
        "health_domains": ["sante.gouv.cg"],
        "season": "Congo/Ubangi river corridor; cross-border with Kinshasa",
    },
    "ERI": {
        "name": "Eritrea", "iso2": "ER", "subregion": "East Africa",
        "adm1": ["Anseba", "Debub", "Debubawi Keyih Bahri", "Gash-Barka", "Maekel",
                 "Semenawi Keyih Bahri"],
        "major_cities": ["Asmara", "Keren", "Massawa", "Assab", "Mendefera", "Barentu"],
        "neighbors": ["DJI", "ETH", "SDN"],
        "search_languages": ["en", "ar", "ti"],
        "disease_terms": ["cholera", "acute watery diarrhoea", "kolera",
                          "\u12ae\u120c\u122b",
                          "\u0627\u0644\u0643\u0648\u0644\u064a\u0631\u0627"],
        # NOTE: shabait.com is the Ministry of INFORMATION / state media, not a
        # health ministry. Eritrea publishes no health-ministry site; this is the
        # only state channel available and should be weighted accordingly.
        "health_domains": ["shabait.com"],
        "season": "Minimal public reporting; treat absence of data as non-reporting unless positively documented",
    },
    "ETH": {
        "name": "Ethiopia", "iso2": "ET", "subregion": "East Africa",
        "adm1": ["Addis Ababa", "Afar", "Amhara", "Benishangul-Gumuz",
                 "Central Ethiopia", "Dire Dawa", "Gambela", "Harari", "Oromia",
                 "Sidama", "Somali", "South Ethiopia",
                 "South West Ethiopia Peoples' Region", "Tigray"],
        "adm1_legacy": {
            # SNNPR was dissolved 19 Aug 2023 into Sidama, South West Ethiopia,
            # Central Ethiopia and South Ethiopia. Keeping it live risked agents
            # coding post-2023 events to a region that no longer exists.
            "pre_2023": ["SNNPR", "Southern Nations Nationalities and Peoples"],
        },
        "major_cities": ["Addis Ababa", "Dire Dawa", "Mekelle", "Gondar", "Hawassa",
                         "Bahir Dar", "Jimma", "Adama"],
        "neighbors": ["DJI", "ERI", "KEN", "SOM", "SSD", "SDN"],
        "search_languages": ["en", "am"],
        "disease_terms": ["cholera", "acute watery diarrhoea", "AWD",
                          "\u12ae\u120c\u122b",
                          "\u12a0\u1320\u12f3\u134a \u1270\u1245\u121b\u1325"],
        "health_domains": ["www.moh.gov.et", "ephi.gov.et"],
        "season": "Reported historically as 'AWD' rather than cholera - search both terms; Oromia/Somali/Amhara foci",
    },
    "GAB": {
        "name": "Gabon", "iso2": "GA", "subregion": "Central Africa",
        "adm1": ["Estuaire", "Haut-Ogooue", "Moyen-Ogooue", "Ngounie", "Nyanga",
                 "Ogooue-Ivindo", "Ogooue-Lolo", "Ogooue-Maritime", "Woleu-Ntem"],
        "major_cities": ["Libreville", "Port-Gentil", "Franceville", "Oyem", "Moanda"],
        "neighbors": ["CMR", "COG", "GNQ"],
        "search_languages": ["fr", "en"],
        "disease_terms": ["cholera", "diarrhee aqueuse aigue"],
        "health_domains": ["sante.gouv.ga"],
        "season": "Rare; Libreville/Port-Gentil importation risk",
    },
    "GHA": {
        "name": "Ghana", "iso2": "GH", "subregion": "West Africa",
        "adm1": ["Ahafo", "Ashanti", "Bono", "Bono East", "Central", "Eastern",
                 "Greater Accra", "North East", "Northern", "Oti", "Savannah",
                 "Upper East", "Upper West", "Volta", "Western", "Western North"],
        "major_cities": ["Accra", "Kumasi", "Tamale", "Sekondi-Takoradi", "Cape Coast", "Tema"],
        "neighbors": ["BFA", "CIV", "TGO"],
        "search_languages": ["en"],
        "disease_terms": ["cholera", "acute watery diarrhoea"],
        "health_domains": ["moh.gov.gh", "ghs.gov.gh"],
        "season": "Greater Accra urban epidemics; rainy season Apr-Jul; 2014 major epidemic",
    },
    "GIN": {
        "name": "Guinea", "iso2": "GN", "subregion": "West Africa",
        "adm1": ["Boke", "Conakry", "Faranah", "Kankan", "Kindia", "Labe", "Mamou", "Nzerekore"],
        "major_cities": ["Conakry", "Nzerekore", "Kankan", "Kindia", "Boke", "Labe"],
        "neighbors": ["CIV", "GNB", "LBR", "MLI", "SEN", "SLE"],
        "search_languages": ["fr", "en"],
        "disease_terms": ["cholera", "diarrhee aqueuse aigue"],
        "health_domains": ["sante.gov.gn", "anss-guinee.org"],
        "season": "Coastal Conakry/Boke foci; rainy season Jun-Oct",
    },
    "GMB": {
        "name": "Gambia", "iso2": "GM", "subregion": "West Africa",
        "adm1": ["Banjul", "Central River", "Kanifing", "Lower River", "North Bank",
                 "Upper River", "West Coast"],
        "major_cities": ["Banjul", "Serekunda", "Brikama", "Bakau", "Farafenni"],
        "neighbors": ["SEN"],
        "search_languages": ["en"],
        "disease_terms": ["cholera", "acute watery diarrhoea"],
        "health_domains": ["moh.gov.gm"],
        "season": "Rare; Gambia river corridor; shares epidemiology with Senegal",
    },
    "GNB": {
        "name": "Guinea-Bissau", "iso2": "GW", "subregion": "West Africa",
        "adm1": ["Bafata", "Biombo", "Bissau", "Bolama", "Cacheu", "Gabu", "Oio",
                 "Quinara", "Tombali"],
        "major_cities": ["Bissau", "Bafata", "Gabu", "Canchungo", "Farim"],
        "neighbors": ["GIN", "SEN"],
        "search_languages": ["pt", "fr", "en"],
        "disease_terms": ["colera", "diarreia aguda aquosa"],
        "health_domains": ["afro.who.int/countries/guinea-bissau"],
        "season": "Bissau urban epidemics; rainy season Jun-Oct; 1994/2005/2008 major epidemics",
    },
    "GNQ": {
        "name": "Equatorial Guinea", "iso2": "GQ", "subregion": "Central Africa",
        "adm1": ["Annobon", "Bioko Norte", "Bioko Sur", "Centro Sur", "Djibloho",
                 "Kie-Ntem", "Litoral", "Wele-Nzas"],
        "major_cities": ["Malabo", "Bata", "Ebebiyin", "Mongomo", "Oyala"],
        "neighbors": ["CMR", "GAB"],
        "search_languages": ["es", "fr", "pt", "en"],
        "disease_terms": ["colera", "diarrea acuosa aguda"],
        "health_domains": ["guineasalud.org"],
        "season": "Rare; limited public surveillance reporting",
    },
    "KEN": {
        "name": "Kenya", "iso2": "KE", "subregion": "East Africa",
        "adm1": ["Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa",
                 "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi",
                 "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu",
                 "Machakos", "Makueni", "Mandera", "Marsabit", "Meru", "Migori", "Mombasa",
                 "Murang'a", "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua",
                 "Nyeri", "Samburu", "Siaya", "Taita-Taveta", "Tana River", "Tharaka-Nithi",
                 "Trans Nzoia", "Turkana", "Uasin Gishu", "Vihiga", "Wajir", "West Pokot"],
        "adm1_legacy": {
            # Counties replaced provinces under the 2010 constitution, effective
            # 2013. All pre-2013 Kenyan reporting - most of the JHU baseline -
            # uses the 8 provinces.
            "pre_2013": ["Central", "Coast", "Eastern", "Nairobi", "North Eastern",
                         "Nyanza", "Rift Valley", "Western"],
        },
        "major_cities": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Garissa"],
        "neighbors": ["ETH", "SOM", "SSD", "TZA", "UGA"],
        "search_languages": ["en", "sw"],
        "disease_terms": ["cholera", "acute watery diarrhoea", "kipindupindu"],
        "health_domains": ["health.go.ke", "kemri.go.ke"],
        "season": "Refugee camps (Dadaab, Kakuma), Nairobi informal settlements, lake and coastal counties; rains Mar-May, Oct-Dec",
    },
    "LBR": {
        "name": "Liberia", "iso2": "LR", "subregion": "West Africa",
        "adm1": ["Bomi", "Bong", "Gbarpolu", "Grand Bassa", "Grand Cape Mount", "Grand Gedeh",
                 "Grand Kru", "Lofa", "Margibi", "Maryland", "Montserrado", "Nimba",
                 "River Cess", "River Gee", "Sinoe"],
        "major_cities": ["Monrovia", "Gbarnga", "Buchanan", "Ganta", "Kakata", "Harper"],
        "neighbors": ["CIV", "GIN", "SLE"],
        "search_languages": ["en"],
        "disease_terms": ["cholera", "acute watery diarrhoea"],
        "health_domains": ["moh.gov.lr", "nphil.gov.lr"],
        "season": "Monrovia (West Point, Clara Town) urban foci; rainy season May-Oct",
    },
}
