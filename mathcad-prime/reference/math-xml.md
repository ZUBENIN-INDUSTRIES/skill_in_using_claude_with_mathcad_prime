# Math XML (namespace `ml:`)

## Contents
- Identifiers and units
- Definitions and evaluations
- Operators
- Functions
- Vectors, matrices, ranges, indices
- Builder cheat sheet (mcdx.py)

## Identifiers and units
```xml
<ml:id labels="VARIABLE" xml:space="preserve">x</ml:id>
<ml:id labels="VARIABLE" xml:space="preserve"><Span xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
   xmlns:pw="clr-namespace:Ptc.Wpf;assembly=Ptc.Core">L<pw:Subscript>1</pw:Subscript></Span></ml:id>   <!-- L₁ -->
<ml:id labels="UNIT" xml:space="preserve">m</ml:id>          <!-- also kg s N kN Pa MPa mm deg Hz … -->
<ml:id labels="FUNCTION" xml:space="preserve">sin</ml:id>
```
Literal subscripts are part of the name (`L_1` ≠ `L[1]`). `labels` and `label-is-contextual="true"` are optional on reads; Mathcad accepts ids without them.

## Definitions and evaluations
| Display | XML |
|---|---|
| `a := expr` | `<ml:define>ID expr</ml:define>` |
| `a := expr = 12 m` | `<ml:define>ID<ml:eval>expr<ml:unitOverride><ml:placeholder/></ml:unitOverride></ml:eval></ml:define>` |
| `expr = ` | `<ml:eval>expr<ml:unitOverride><ml:placeholder/></ml:unitOverride></ml:eval>` |
| result shown in kN | `<ml:unitOverride><ml:id labels="UNIT">kN</ml:id></ml:unitOverride>` |
| `f(t) := …` | `<ml:define><ml:function>ID<ml:boundVars>ID_t</ml:boundVars></ml:function>expr</ml:define>` |
| `v[4] := 0` | `<ml:define><ml:apply><ml:indexer/>ID_v<ml:real>4</ml:real></ml:apply><ml:real>0</ml:real></ml:define>` |
| `a = b` (bold, solve blocks) | `<ml:apply><ml:equal/>a b</ml:apply>` |
| `12 m` | `<ml:apply><ml:mult/><ml:real>12</ml:real>UNIT</ml:apply>` (`<ml:scale/>` also occurs, e.g. `45 deg`) |

## Operators
`<ml:apply><ml:OP/> args…</ml:apply>` — binary ops nest left: a+b+c = plus(plus(a,b),c).
`plus minus mult div pow neg equal indexer absval nthRoot transpose matcol scale`
- √x: `<ml:apply><ml:nthRoot/><ml:placeholder/>x</ml:apply>`; |z|: `absval`; column ⟨0⟩: `matcol`.
- Visible parentheses: `<ml:parens>…</ml:parens>` (needed for display only where you want them).
- Imaginary unit: usually a user variable `j := √-1` — check the worksheet.

## Functions
`<ml:apply><ml:id labels="FUNCTION">Re</ml:id> arg</ml:apply>` — `Re Im arg exp sin cos ln …`.
No complex-conjugate builder is provided; write `Re(z) − j·Im(z)` instead of guessing the operator.

## Vectors, matrices, ranges, indices
- Matrix cells are stored **column-major**: `<ml:matrix rows="2" cols="2">a11 a21 a12 a22</ml:matrix>` (`matrix(rows)` takes row-major input).
- Range `t := 0, 0.00005 s .. 0.01 s`: `<ml:range><ml:sequence>0 (0.00005·s)</ml:sequence>(0.01·s)</ml:range>`.
- Index base = ORIGIN from settings (0 or 1).

## Builder cheat sheet (mcdx.py)
```python
ident('L_max'); num(2); qty(18, 'kN'); par(x); fn('Re', ident('z')); index('v', 4)
ap('div', num(1), ap('mult', ident('E'), ident('I_y')))     # 1/(E·I_y)
chain([(1, ident('a')), (-1, ap('mult', ident('b'), ident('c')))])   # a − b·c
matrix([[ident('k_11'), ap('neg', ident('k_12'))], [ap('neg', ident('k_21')), ident('k_22')]])
```
