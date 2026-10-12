# .mcdx file format (Mathcad Prime 6–10)

## Contents
- Package
- worksheet.xml
- Region kinds
- result.xml
- settings
- Pictures, plots, solve blocks

## Package
`.mcdx` is an OPC zip. Rewrite it with the same entry order and compression (`Mcdx.save` does).
| Entry | Meaning |
|---|---|
| `mathcad/worksheet.xml` | all regions (math, text, pictures, plots, solve blocks) and their positions |
| `mathcad/result.xml` | cached results, keyed by `resultRef`; stale after you edit |
| `mathcad/settings/calculation.xml` | `array-origin` (ORIGIN), `automatic-recalculation`, unit system |
| `mathcad/settings/presentation.xml` | fonts, number format defaults |
| `mathcad/xaml/FlowDocumentN.XamlPackage` | one zip per text block, `Xaml/Document.xaml` inside |
| `mathcad/media/ImageN.png` | pictures |
| `mathcad/_rels/worksheet.xml.rels` | maps `item-idref="R…"` → package path |

## worksheet.xml
`<worksheet><regions><region region-id="N" top left width height actualWidth actualHeight>…</region>…</regions></worksheet>`
- `region-id` unique integers; Mathcad **renumbers them on save**.
- Top-level regions have `top`/`left` (page coordinates, WPF px). Regions inside a text block have `text-caret-position` instead; regions inside a solve block have local `top`/`left`.
- Math region: `<math resultRef="K">…</math>` + optional `<formattingOverride FontSize="11"/>`, `<resultFormat>…</resultFormat>`. New regions need a unique `resultRef`.

## Region kinds
| Child element | Kind |
|---|---|
| `<math>` | expression / definition / evaluation |
| `<text is-text-block="true" item-idref>` + `<FlowDocument …/>` + `<regions>` | text block with inline math |
| `<picture><png item-idref display-width display-height/></picture>` | image |
| `<plot><xyPlot>…</xyPlot></plot>` | 2D plot |
| `<solveblock><regions>…</regions></solveblock>` | Given/Find block |

## result.xml
`<resultData result-id="K" calculation-status="Synchronized|Pending">` with `<ml:result>`:
- real: `<ml:real>`, complex: `<ml:complex><ml:real/><ml:imag/></ml:complex>`, with units: `<ml:unitedValue>…<u:unitMonomial>` (SI base units: meter, newton, second, …), matrices: `<ml:matrix>`.
- After editing, results are only valid in the copy Mathcad saved (SaveAs). A region shown without “=” may keep an old cached value — harmless.

## settings
`<builtInVariables array-origin="0|1" …>` — index base for `v[0]` vs `v[1]`. `<calculationBehavior automatic-recalculation="true">`.

## Pictures, plots, solve blocks
- **Picture:** bytes in `mathcad/media/…png`; size = region `width/height` + `display-width/height` (all must agree). Replace bytes in place, keep the file name.
- **Plot:** `<trace resultRef>` per curve; axes `<xAxis start end>` / `<yAxis …>`; `<xyDomain auto-scale="true">` with `<startValue>/<endValue>` — a fixed `<endValue><ml:real>0</ml:real></endValue>` clips data above 0: replace by `<endValue><ml:placeholder /></endValue>` for auto range. Plot equations live in `<plotEquations><plotEquation><math>…`.
- **Solve block:** `<solveblock><regions>` of text regions (`solve-block-category="constraint"`) whose inline math are `<ml:apply><ml:equal/> lhs rhs</ml:apply>` (bold “=”), followed by a define with `Find`: `<ml:define><ml:matrix>vars</ml:matrix> Find <ml:sequence>vars</ml:sequence></ml:define>`. Edit the constraint equations; keep the structure.
