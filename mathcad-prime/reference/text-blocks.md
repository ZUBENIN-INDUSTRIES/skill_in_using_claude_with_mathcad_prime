# Text blocks and inline math

## Contents
- Structure
- Caret positions (the rule)
- Editing text safely
- Adding and removing inline math
- Things Mathcad ignores

## Structure
A text block region references a XamlPackage (zip) with `Xaml/Document.xaml`:
`<Section …FontSize="18.67"><Paragraph><Run>text</Run>…</Paragraph>…</Section>`.
Subscripts in plain text: `<Ptc.Controls.Text:SubscriptRun …>1</Ptc.Controls.Text:SubscriptRun>`.
Inline math regions are listed inside the text region in worksheet.xml (`<text …><regions>…</regions></text>`), each with `text-caret-position`; in the XAML each one sits on an anchor run — usually `<Run> </Run>`, sometimes `<Run style="Normal"> </Run>` — a single space.

## Caret positions (the rule)
`text-caret-position` = index, in the WPF symbol stream of the XAML, of the symbol just before the anchor `<Run …>` tag.
Symbol stream: every tag = 1 symbol (self-closing = 2), every character = 1, the outer `<Section>` included.
Consequence: changing text length anywhere before an inline region (e.g. “80” → “110”) moves it to the wrong place; adding a paragraph moves everything after it.

## Editing text safely
`Mcdx` marks each anchor run with `§id§` (inside the tag, so symbol counts do not change), lets you edit, then recomputes every caret from the markers on `save()`.
```python
doc.replace_text(14, 'Определить:', 'Требуется определить:')         # asserts exactly one match
doc.edit_xaml(14, lambda x: x.replace('>old<', '>new<'))              # free-form; keep §id§ markers
```
- Numbers in text are often split across runs (`= 1` + `60` for 160): match per run, assert the old digits.
- Text written by the user (headings, wording) — change only what was asked.
- A longer sentence can wrap to a second line → the block grows → regions below overlap (see layout.md). Prefer wording of similar length.

## Adding and removing inline math
```python
nid = doc.clone_inline(17, where='after')                 # same line, after region 17 (tab between)
nid = doc.clone_inline(11, where='before', anchor_rid=12) # same line, before region 12
nid = doc.clone_inline(16, where='paragraph')             # new paragraph after 16's paragraph
doc.set_define(nid, 'A_2', ap('mult', ident('b_2'), ident('h_2')))
doc.delete(16)                                            # region + its anchor run
```
- A clone gets a new `region-id` and `resultRef`; then overwrite its content.
- In many worksheets the unit after a value is a separate inline region (`L := 0.3` + `m`) — choose the anchor so the new formula does not land between a value and its unit.
- `where='after'`/`'before'` keeps the block height (best); `'paragraph'` adds a line (needs relayout).

## Things Mathcad ignores
Paragraph `Margin`, `LineHeight`, and spacer runs with tiny fonts are overridden on load. To change line pitch of a plain text block use the `Section` `FontSize`.
