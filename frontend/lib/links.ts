const enc = encodeURIComponent;
const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

/** Job-search deep links that open the original sites, pre-filtered for the given company (or all companies). */
export function jobSearchLinks(company = "", opts: { india?: boolean; fresher?: boolean } = { india: true, fresher: true }) {
  const role = opts.fresher ? "software engineer fresher" : "software engineer";
  const kw = company ? `${company} software engineer` : role;
  const loc = opts.india ? "India" : "";
  const li = new URLSearchParams({ keywords: kw, f_TPR: "r604800" });
  if (loc) li.set("location", loc);
  if (opts.fresher) li.set("f_E", "1,2");
  const links: [string, string][] = [
    ["LinkedIn", `https://www.linkedin.com/jobs/search/?${li}`],
    ["Naukri", company
      ? `https://www.naukri.com/${slug(company)}-jobs${opts.fresher ? "?experience=0" : ""}`
      : `https://www.naukri.com/software-engineer-jobs${opts.fresher ? "?experience=0" : ""}`],
    ["Indeed", `https://${opts.india ? "in." : ""}indeed.com/jobs?q=${enc(kw)}&l=${enc(loc)}&fromage=7`],
    ["Glassdoor", `https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword=${enc(kw)}`],
    ["Wellfound", `https://wellfound.com/role/l/software-engineer/${opts.india ? "india" : "remote"}`],
  ];
  if (!company && opts.fresher) {
    links.push(
      ["Internshala", "https://internshala.com/jobs/software-development-jobs/"],
      ["Unstop", "https://unstop.com/jobs"],
      ["Instahyre", "https://www.instahyre.com/search-jobs/"],
      ["Cutshort", "https://cutshort.io/jobs"],
    );
  }
  return links;
}
