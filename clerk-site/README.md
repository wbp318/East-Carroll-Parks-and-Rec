# East Carroll Parish Clerk of Court Website (Draft)

A draft replacement for `eastcarrollclerk.com`, built 2026-11-06 from the content of the current site. Prepared as an offer to the Clerk of Court's office. **Nothing here is live.** Every page carries a yellow "Draft for review" banner until the office approves it. See `docs/CLERK_WEBSITE_ASSESSMENT.md` for why the current site is failing.

## What it is

Plain HTML and one stylesheet. There is no build step, no database, no scripts, no tracking, and no outside fonts, so it is fast on slow rural connections and has nothing to patch. Any free static host with automatic HTTPS can serve it.

| File | Page |
|---|---|
| `index.html` | Home: welcome letter, quick links, hours, address |
| `records.html` | Online records through eClerksLA |
| `fees.html` | All fees from the current site, as tables |
| `services.html` | Marriage licenses, birth and death certificates, recording requirements, elections |
| `court.html` | 6th Judicial District Court and the full jury duty guide |
| `contact.html` | Address, phone, fax, hours, where to go in the courthouse |
| `404.html` | Page-not-found page |
| `styles.css` | All styling |
| `policies/` | Folder for the office's PDFs (empty until the office supplies them) |

**To view it:** open `index.html` in any browser.

## Fixes over the current site

- **Works over HTTPS** once hosted, so browsers stop warning visitors.
- **Jury booklet named the wrong parish.** The current site says jurors are drawn from "St. Landry Parish." That is fixed to East Carroll.
- **Two dead PDF links:** the Sexual Harassment Policy and the eClerksLA Terms of Use both return "not found" today. The draft links to `policies/` so the office can re-post them.
- Typos fixed ("proerty," "Additonal," "preemptory," "statue," "D-214" corrected to DD-214, "Q W-2" corrected to "A W-2"). The jury guide's "State Attorney" changed to the District Attorney, which is the Louisiana office. UCC wording about 2001-era forms removed.
- Readable on phones, with real text throughout (the old builder used fixed layouts), headings for screen readers, a skip link, and large tap targets.

## Review checklist for the Clerk's office

Nothing below has been changed from the current site's content except as noted. The office should confirm each item before launch.

**Names and contacts**
- [ ] Exact name and spelling to display for the Clerk (draft shows "Rene Thomas Williams," the name in the Clerks of Court Association directory and the FY2023 audit)
- [ ] Office hours (draft: Monday to Friday, 8:30 a.m. to 4:30 p.m., from public listings)
- [ ] Fax number (318) 559-0037 (from the Louisiana Department of Health directory)
- [ ] An office email address to publish, if wanted (the old contact form went through GoDaddy and is not carried over)
- [ ] 6th JDC judges and phone numbers are current (Angela L. Claxton, Division A; Laurie R. Brister, Division B)

**Fees** (copied exactly from the current site)
- [ ] Every fee on `fees.html` is current, especially recording, mortgage certificates, and UCC
- [ ] "51 or more pages, per page: $5.00": confirm whether this is $5 per page for every page or $300 plus $5 per page over 50
- [ ] Marriage license $32.50, cash only
- [ ] Juror pay $25.00 per day plus mileage

**Legal wording to confirm**
- [ ] Marriage license rules for applicants under 18. The current site's wording ("must be over 18," then rules for under 18 and under 16) contradicts itself, and Louisiana's law on minors marrying has changed in recent years. The draft says "parental consent and other requirements apply; please call the office" until the office supplies the current rule.
- [ ] 24-hour wait after the license and the 30-day wait after a final divorce
- [ ] Elections section wording (the Clerk as chief election officer of the parish; registration handled by the Registrar of Voters)

**Documents to supply** (save into `policies/` with these exact names)
- [ ] `sexual-harassment-policy.pdf`: the office's current policy. Louisiana's sexual harassment law for public agencies (R.S. 42:341 et seq.) requires a written policy.
- [ ] `eclerksla-terms-of-use.pdf`: the East Carroll eClerksLA terms of use agreement

## How to launch (after approval)

The domain `eastcarrollclerk.com` is registered through July 10, 2028 and stays in the office's account. Only its DNS records change.

1. **Find who holds the domain account** (registrar: Wild West Domains, a GoDaddy reseller platform). The office needs the login, or the web designer who holds it must cooperate.
2. **Remove the draft banner:** delete the one `<div class="draft-banner" ...>` line near the top of each page.
3. **Host it free with automatic HTTPS:** create a Cloudflare Pages or GitHub Pages project under an account the office owns, and upload this folder.
4. **Point the domain:** add the host's DNS records (a CNAME for `www`, plus the apex records the host lists) in the domain account. HTTPS certificates are issued automatically within minutes to hours.
5. **Check:** load `https://eastcarrollclerk.com` and `https://www.eastcarrollclerk.com` in Chrome on a phone and a computer, click every link, then cancel the old GoDaddy Website Builder plan if it carries a fee.
6. **Optional:** request a free `.gov` domain from CISA at https://get.gov/ and point it at the same site.

## Editing later

- **Fees:** in `fees.html`, each fee is one table row, `<tr><td>Item</td><td class="fee">$0.00</td></tr>`. Change the number and save.
- **Hours or phone:** these appear on every page in the footer, plus `index.html` and `contact.html`. Search all files for the old value and replace it.
- **Adding a PDF:** put it in `policies/` and link it as `policies/file-name.pdf`.
