Found while reconciling last month's invoices against the ledger.

## The problem

Invoices are rendered to PDF by a third-party library. It is quick to adopt, but on our main path it hides or guesses facts we then reconstruct:

- **Fonts.** It substitutes a fallback font when the configured one is missing, so the printed total can shift by a column.
- **Rounding.** It rounds currency amounts itself, so the PDF total can differ from the ledger total by a cent.
- **Page breaks.** It splits a line item across two pages without notice.

Credit notes already bypass it: they are rendered as plain text.

## Proposal

- **One renderer interface of our own, one implementation per output format.** The format an invoice requests picks the implementation.
- **A native PDF renderer** for invoices, where totals and page layout must match the ledger exactly.
- **A plain-text renderer** for every other format, so existing exports keep working without new code.

## Rejected alternatives

- **Patch the library.** Fixes the rounding, keeps the font and page-break guesses.
- **Stay on the library everywhere.** Keeps every guess listed above.

## Cost

Moving invoices off the library changes every rendered PDF's bytes, so every stored reference PDF is regenerated at once. Do it once, deliberately, not inside another task.

## Acceptance

- An invoice goes through the native renderer: its PDF total equals the ledger total to the cent.
- An export in a format with no native renderer completes through the plain-text renderer.
- No line item is split across two pages.
- The reference PDFs are regenerated once, and the regeneration is noted where invoice totals are compared.
