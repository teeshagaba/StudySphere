"""Company directory: official careers pages, interview process and focus areas."""

# name -> profile
COMPANY_PROFILES: dict[str, dict] = {
    "Google": {
        "careers": "https://www.google.com/about/careers/applications/jobs/results/",
        "roles": ["SWE L3", "SWE L4", "STEP Intern"],
        "process": ["Online assessment", "Phone screen (DSA)", "4-5 onsite rounds: DSA + Googleyness"],
        "focus": ["Graph", "Dynamic Programming", "Binary Search", "Trie"],
    },
    "Amazon": {
        "careers": "https://www.amazon.jobs/en/",
        "roles": ["SDE I", "SDE II", "SDE Intern"],
        "process": ["Online assessment (2 DSA + work-style)", "3-4 loop rounds: DSA + Leadership Principles", "Bar raiser"],
        "focus": ["Arrays", "Binary Tree", "Graph", "Heap"],
    },
    "Microsoft": {
        "careers": "https://careers.microsoft.com/",
        "roles": ["SWE", "SWE II", "Explore Intern"],
        "process": ["Online assessment", "3-4 technical rounds", "AA (as-appropriate) round"],
        "focus": ["Linked List", "Binary Tree", "Strings", "Design"],
    },
    "Meta": {
        "careers": "https://www.metacareers.com/jobs",
        "roles": ["E3 Software Engineer", "E4 Software Engineer", "SWE Intern"],
        "process": ["Recruiter call", "Technical screen (2 problems / 45 min)", "Onsite: 2 coding + system design + behavioral"],
        "focus": ["Arrays", "Strings", "Binary Tree", "Graph"],
    },
    "Apple": {
        "careers": "https://jobs.apple.com/",
        "roles": ["Software Engineer", "ICT2/ICT3"],
        "process": ["Recruiter screen", "Technical phone screen", "Team-specific onsite"],
        "focus": ["Arrays", "Linked List", "Design"],
    },
    "Adobe": {
        "careers": "https://careers.adobe.com/us/en",
        "roles": ["MTS", "Computer Scientist", "Intern"],
        "process": ["Online test (aptitude + DSA)", "2-3 technical rounds", "Director / HR round"],
        "focus": ["Arrays", "Dynamic Programming", "Binary Tree"],
    },
    "Nvidia": {
        "careers": "https://www.nvidia.com/en-us/about-nvidia/careers/",
        "roles": ["System Software Engineer", "Deep Learning Engineer"],
        "process": ["Recruiter screen", "Technical rounds (DSA, C/C++, OS)", "Hiring manager"],
        "focus": ["Linked List", "Bit Manipulation", "Design"],
    },
    "Goldman Sachs": {
        "careers": "https://www.goldmansachs.com/careers/",
        "roles": ["Analyst - Engineering", "Summer Analyst"],
        "process": ["HackerRank OA", "CoderPad round", "Superday (3-5 rounds)"],
        "focus": ["Arrays", "Dynamic Programming", "Math"],
    },
    "Uber": {
        "careers": "https://www.uber.com/us/en/careers/",
        "roles": ["Software Engineer I/II"],
        "process": ["OA", "Phone screen", "Onsite: DSA, system design, collaboration"],
        "focus": ["Graph", "Design", "Hashing"],
    },
    "Flipkart": {
        "careers": "https://www.flipkartcareers.com/",
        "roles": ["SDE 1", "SDE 2"],
        "process": ["OA", "Problem solving / DS round", "Machine coding round", "Hiring manager"],
        "focus": ["Graph", "Dynamic Programming", "Design"],
    },
    "Walmart": {
        "careers": "https://careers.walmart.com/",
        "roles": ["Software Engineer II", "Software Engineer III"],
        "process": ["OA", "2 technical rounds", "Hiring manager"],
        "focus": ["Arrays", "Design", "Graph"],
    },
    "Bloomberg": {
        "careers": "https://www.bloomberg.com/company/careers/",
        "roles": ["Software Engineer", "SWE Intern"],
        "process": ["Phone screen (DSA)", "2 onsite coding rounds", "System design (experienced)", "HR + manager"],
        "focus": ["Strings", "Linked List", "Design"],
    },
    "LinkedIn": {
        "careers": "https://careers.linkedin.com/",
        "roles": ["Software Engineer", "Senior Software Engineer"],
        "process": ["Phone screen", "Onsite: coding, system design, host manager"],
        "focus": ["Design", "Binary Tree", "Arrays"],
    },
    "Atlassian": {
        "careers": "https://www.atlassian.com/company/careers",
        "roles": ["Software Engineer", "Graduate SWE"],
        "process": ["Karat / OA", "Code design round", "Values + management rounds"],
        "focus": ["Design", "Hashing", "Heap"],
    },
    "Salesforce": {
        "careers": "https://careers.salesforce.com/",
        "roles": ["AMTS", "MTS"],
        "process": ["OA", "2-3 technical rounds", "Hiring manager"],
        "focus": ["Arrays", "Strings", "Dynamic Programming"],
    },
    "Oracle": {
        "careers": "https://www.oracle.com/careers/",
        "roles": ["Member of Technical Staff"],
        "process": ["OA", "2-3 technical rounds (DSA, DBMS, OS)", "HR"],
        "focus": ["Arrays", "Linked List", "Strings"],
    },
}

# Public job-board feeds (Greenhouse / Lever board tokens). Unknown tokens are skipped gracefully.
GREENHOUSE_BOARDS = {
    "stripe": "Stripe", "airbnb": "Airbnb", "databricks": "Databricks", "figma": "Figma", "discord": "Discord",
    "robinhood": "Robinhood", "coinbase": "Coinbase", "dropbox": "Dropbox", "pinterest": "Pinterest",
    "gitlab": "GitLab", "cloudflare": "Cloudflare", "mongodb": "MongoDB", "reddit": "Reddit", "lyft": "Lyft",
    "instacart": "Instacart", "groww": "Groww", "rubrik": "Rubrik", "samsara": "Samsara",
}
LEVER_BOARDS = {
    "palantir": "Palantir", "spotify": "Spotify", "cred": "CRED", "meesho": "Meesho", "paytm": "Paytm", "zeta": "Zeta",
}
# Workday career sites: (host, tenant, site) -> company
WORKDAY_SITES = {
    ("nvidia.wd5.myworkdayjobs.com", "nvidia", "NVIDIAExternalCareerSite"): "Nvidia",
    ("salesforce.wd12.myworkdayjobs.com", "salesforce", "External_Career_Site"): "Salesforce",
    ("adobe.wd5.myworkdayjobs.com", "adobe", "external_experienced"): "Adobe",
    ("intel.wd1.myworkdayjobs.com", "intel", "External"): "Intel",
    ("mastercard.wd1.myworkdayjobs.com", "mastercard", "CorporateCareers"): "Mastercard",
    ("paypal.wd1.myworkdayjobs.com", "paypal", "jobs"): "PayPal",
}
# Eightfold-powered career sites: (host, domain) -> company
EIGHTFOLD_SITES = {
    ("explore.jobs.netflix.net", "netflix.com"): "Netflix",
}

# Extra companies (no curated interview profile). name -> careers URL ("" = use web search).
MORE_COMPANIES = {
    "Netflix": "https://jobs.netflix.com/", "Intuit": "https://jobs.intuit.com/", "Cisco": "https://jobs.cisco.com/",
    "Qualcomm": "https://careers.qualcomm.com/", "Intel": "https://jobs.intel.com/", "IBM": "https://www.ibm.com/careers",
    "Samsung R&D": "https://www.samsung.com/in/about-us/careers/", "Texas Instruments": "https://careers.ti.com/",
    "JPMorgan Chase": "https://careers.jpmorgan.com/", "Morgan Stanley": "https://www.morganstanley.com/careers",
    "Visa": "https://corporate.visa.com/en/jobs/", "Mastercard": "https://careers.mastercard.com/",
    "PayPal": "https://careers.pypl.com/", "ServiceNow": "https://careers.servicenow.com/",
    "D. E. Shaw": "https://www.deshawindia.com/careers", "Tower Research": "https://www.tower-research.com/open-positions",
    "Media.net": "https://careers.media.net/", "Sprinklr": "https://www.sprinklr.com/careers/",
    "Zoho": "https://www.zoho.com/careers/", "Freshworks": "https://www.freshworks.com/company/careers/",
    "Swiggy": "https://careers.swiggy.com/", "Zomato": "https://www.zomato.com/careers",
    "Razorpay": "https://razorpay.com/jobs/", "PhonePe": "https://www.phonepe.com/careers/",
    "Paytm": "https://paytm.com/careers/", "CRED": "https://careers.cred.club/", "Meesho": "https://www.meesho.io/careers",
    "Zepto": "", "Groww": "", "Postman": "https://www.postman.com/company/careers/",
    "BrowserStack": "https://www.browserstack.com/careers", "Juspay": "", "Rubrik": "https://www.rubrik.com/company/careers",
    "Nutanix": "https://www.nutanix.com/company/careers", "Stripe": "https://stripe.com/jobs",
    "Databricks": "https://www.databricks.com/company/careers", "Coinbase": "https://www.coinbase.com/careers",
    "TCS": "https://www.tcs.com/careers", "Infosys": "https://www.infosys.com/careers/",
    "Wipro": "https://careers.wipro.com/", "Accenture": "https://www.accenture.com/in-en/careers",
    "Deloitte": "https://www2.deloitte.com/in/en/careers.html", "Cognizant": "https://careers.cognizant.com/",
    "HCLTech": "https://www.hcltech.com/careers", "Capgemini": "https://www.capgemini.com/careers/",
}
