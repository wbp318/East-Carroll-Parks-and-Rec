# East Carroll Parish Clerk of Court Website: Assessment and Fix Plan

Checked 2026-11-06 from outside the office (no account access). Site: `eastcarrollclerk.com`.

## 1. What is wrong

The site is not deleted. It is still served over plain HTTP, and every page loads. It looks down because **secure (HTTPS) connections fail**.

| Check | Result |
|---|---|
| Domain registration | Active. Registered 2014-07-10, **expires 2028-07-10**, registrar Wild West Domains (a GoDaddy reseller platform), locked against transfer and deletion. Last changed 2026-07-11. |
| DNS | Resolves to GoDaddy hosting (nameservers `NS45/NS46.DOMAINCONTROL.COM`) |
| `http://www.eastcarrollclerk.com` | 200 OK, all six pages load (Home, Pricing, Eclerksla, Services, Court Information, Contact) |
| `https://www.eastcarrollclerk.com` | **Fails.** The server presents a certificate for `*.secureserversites.net`, not for the clerk's domain, so browsers show "Your connection is not private" |
| Platform | GoDaddy Website Builder v7 (the legacy builder; template build dated December 2023) |
| Sexual Harassment Policy link (PDF) | **404, file missing** |

**Why it broke now.** Google announced that Chrome 154 (October 2026) turns on "Always Use Secure Connections" by default for public sites. Chrome now tries HTTPS first and warns before falling back to HTTP. A site that has no valid certificate for its own name will look broken or unsafe to most visitors as of this fall, even though nothing on the server changed.

## 2. Who has to be involved

- **The account holder.** The domain sits on a reseller platform, so the GoDaddy-family account may belong to the office, to a former web designer, or to a vendor. Step one is to find out who holds the login. The domain must stay in the Clerk of Court's name and account, whoever does the work.
- **The clerk.** She is the elected official and decides the content and vendor. Any paid work goes through her office's normal purchasing, and its cost and its funding source are her call.

## 3. Fix options

| Option | What it is | Cost | Time | Notes |
|---|---|---|---|---|
| A. Quick patch | In the existing GoDaddy account, add a certificate that covers `eastcarrollclerk.com` (an SSL add-on, or moving the site to GoDaddy's current builder, which includes SSL) | Roughly the cost of an SSL add-on or plan upgrade; check the account | One afternoon once someone has the login | Fixes the warning only. The legacy builder stays. |
| B. Rebuild on free static hosting (recommended) | A plain, fast, accessible site with the same pages, served by a free static host with automatic HTTPS (Cloudflare Pages or GitHub Pages). Point the domain's DNS at it; the domain stays where it is | Domain renewal only (already paid through 2028) | 1 to 2 weeks including review | No monthly hosting bill, no builder lock-in, and anyone in the office can edit it with simple instructions |
| C. Add a .gov domain | Request `eastcarrollclerk.gov` (or similar) from CISA's .gov registry, free to qualifying U.S. government organizations; keep the .com redirecting | Free | Weeks for CISA approval; the elected official authorizes | Tells the public the site is official, and pairs with the cybersecurity grants in the funding plan |

The recommended path is **A now if the login is easy to find, then B and C together**.

## 4. What a rebuilt site should carry

- Current clerk name, hours, address (400 First Street, Suite 3, Lake Providence, LA 71254), phone (318) 559-2399, fax (318) 559-0037
- Fee schedule (civil costs, certificates, mortgage certificates), kept in one easy-to-edit file
- Marriage license requirements
- 6th Judicial District Court information and the juror booklet
- eClerksLA link for remote records access, with its terms
- Elections: the clerk's role as the parish's chief election officer, with links to the Secretary of State voter portal
- Restored policy PDFs, including the missing Sexual Harassment Policy
- Fraud reporting link to the Legislative Auditor, which the current site already carries
- Accessibility basics: readable on phones, real text instead of images of text, and alt text on images

## 5. The offer to make

"Your site still exists, but browsers are now blocking it because it has no security certificate. I can get the warning fixed quickly and then rebuild it so it costs nothing to host, comes up correctly on phones, and you control it. Your office keeps the domain and the account."

## 6. Sources

- Domain registration data (RDAP), Verisign: https://rdap.verisign.com/com/v1/domain/eastcarrollclerk.com
- Louisiana Clerks of Court Association directory: https://www.laclerksofcourt.org/clerks-of-court/
- Google, HTTPS by default in Chrome (Oct 28, 2025): https://blog.google/security/https-by-defau/
- CyberInsider, Chrome HTTPS default from October 2026: https://cyberinsider.com/chrome-will-default-to-https-for-all-public-sites-starting-october-2026/
- CISA .gov registration: https://get.gov/
