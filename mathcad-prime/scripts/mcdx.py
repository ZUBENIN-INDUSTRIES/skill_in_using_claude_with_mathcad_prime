"""mcdx.py - read, edit and write PTC Mathcad Prime worksheets (.mcdx) without Mathcad.

Library usage (import from a script placed anywhere):
    import sys; sys.path.insert(0, r'<skill>/scripts'); from mcdx import *
    doc = Mcdx.load('in.mcdx')
    doc.set_define(17, 'q_1', ap('div', ident('F'), ident('L_1')), eval_=True)
    doc.save('out.mcdx')

CLI:
    python mcdx.py dump  <file.mcdx>     readable list of all regions (id, kind, caret/top, formula)
    python mcdx.py texts <file.mcdx>     text of every text block, paragraph by paragraph
    python mcdx.py region <file.mcdx> <id>  raw XML of one leaf region
Requires only the Python standard library.
"""
import html
import io
import re
import struct
import sys
import zipfile

GRID = 18.897637795275591      # Mathcad snaps top-level region 'top' to this (0.5 cm in WPF px)
PAGE_W = 642.52                # usable page width in WPF px (A4, default margins)
MK = '§'                  # caret marker character used inside <Run> tags while editing XAML

# ----------------------------------------------------------------------------- math XML builders
SPAN = ('<Span xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
        'xmlns:pw="clr-namespace:Ptc.Wpf;assembly=Ptc.Core">')


def ident(name, labels='VARIABLE'):
    """'L_1' -> L with literal subscript 1; 'x' -> x. Greek/Cyrillic allowed."""
    if '_' in name:
        a, b = name.split('_', 1)
        return '<ml:id labels="%s" xml:space="preserve">%s%s<pw:Subscript>%s</pw:Subscript></Span></ml:id>' % (labels, SPAN, a, b)
    return '<ml:id labels="%s" xml:space="preserve">%s</ml:id>' % (labels, name)


def unit(u):
    return '<ml:id labels="UNIT" xml:space="preserve">%s</ml:id>' % u


def num(x):
    return '<ml:real>%s</ml:real>' % x


def ap(op, *args):
    """operator application: plus minus mult div pow neg equal indexer nthRoot absval scale ..."""
    return '<ml:apply><ml:%s />%s</ml:apply>' % (op, ''.join(args))


def fn(name, *args):
    """built-in/user function call, e.g. fn('Re', ident('z'))"""
    return '<ml:apply>%s%s</ml:apply>' % (ident(name, 'FUNCTION'), ''.join(args))


def par(x):
    return '<ml:parens>%s</ml:parens>' % x


def qty(value, u):
    """number with unit: 18 kN"""
    return ap('mult', num(value), unit(u))


def index(var, k):
    return ap('indexer', ident(var), num(k))


def chain(terms):
    """[(+1, xml), (-1, xml), ...] -> left-nested a + b - c ; a leading negative term becomes neg."""
    acc = None
    for s, t in terms:
        if acc is None:
            acc = t if s > 0 else ap('neg', t)
        else:
            acc = ap('plus' if s > 0 else 'minus', acc, t)
    return acc if acc is not None else num(0)


def matrix(rows):
    """rows given row-major (list of lists of xml); Mathcad stores cells column-major."""
    r, c = len(rows), len(rows[0])
    cells = ''.join(rows[i][j] for j in range(c) for i in range(r))
    return '<ml:matrix rows="%d" cols="%d">%s</ml:matrix>' % (r, c, cells)


def vrange(start, step_second, end):
    """range variable start, second .. end (each arg is xml)"""
    return '<ml:range><ml:sequence>%s%s</ml:sequence>%s</ml:range>' % (start, step_second, end)


# ----------------------------------------------------------------------------- WPF symbol positions
def symbols(xaml):
    """WPF TextPointer symbol stream: each tag = 1 symbol (self-closing = 2), each char = 1."""
    out = []
    for m in re.finditer(r'<[^>]+>|[^<]+', xaml):
        t = m.group(0)
        if t.startswith('<'):
            out.append(('T', t, m.start()))
            if t.endswith('/>'):
                out.append(('T', t, m.start()))
        else:
            for ch in html.unescape(t):
                out.append(('c', ch, m.start()))
    return out


def _pkg_read(b):
    return zipfile.ZipFile(io.BytesIO(b)).read('Xaml/Document.xaml').decode('utf-8')


def _pkg_write(b, x):
    inner = zipfile.ZipFile(io.BytesIO(b))
    o = io.BytesIO()
    with zipfile.ZipFile(o, 'w') as z:
        for ii in inner.infolist():
            d = inner.read(ii)
            if ii.filename == 'Xaml/Document.xaml':
                d = x.encode('utf-8')
            z.writestr(ii, d, compress_type=ii.compress_type)
    return o.getvalue()


# ----------------------------------------------------------------------------- document
class Mcdx:
    def __init__(self, zin, files):
        self._infos = zin.infolist()
        self.files = files
        self.ws = files['mathcad/worksheet.xml'].decode('utf-8')
        self.rels = files['mathcad/_rels/worksheet.xml.rels'].decode('utf-8')
        self._xaml = {}            # rid -> marked xaml being edited
        ids = [int(v) for v in re.findall(r'region-id="(\d+)"', self.ws)]
        refs = [int(v) for v in re.findall(r'resultRef="(\d+)"', self.ws)]
        self._next_id = max(ids) + 1
        self._next_ref = (max(refs) + 1) if refs else 0

    # -- io
    @classmethod
    def load(cls, path):
        zin = zipfile.ZipFile(path)
        return cls(zin, {i.filename: zin.read(i) for i in zin.infolist()})

    def save(self, path):
        for rid in list(self._xaml):
            self._commit_text(rid)
        assert MK not in self.ws
        self.files['mathcad/worksheet.xml'] = self.ws.encode('utf-8')
        with zipfile.ZipFile(path, 'w') as z:
            for info in self._infos:
                z.writestr(info, self.files[info.filename], compress_type=info.compress_type)

    def settings(self):
        """array-origin (ORIGIN) etc. from settings/calculation.xml"""
        s = self.files['mathcad/settings/calculation.xml'].decode('utf-8-sig')
        return dict(re.findall(r' ([\w-]+)="([^"]*)"', s))

    # -- region access (leaf regions = math/picture/plot; text blocks are containers)
    def region(self, rid):
        m = re.search(r'<region region-id="%d"[^>]*>(?:(?!<region ).)*?</region>' % rid, self.ws, re.S)
        if not m:
            raise KeyError('leaf region %d not found (text blocks: use text APIs)' % rid)
        return m

    def get(self, rid):
        return self.region(rid).group(0)

    def put(self, rid, xml):
        m = self.region(rid)
        self.ws = self.ws[:m.start()] + xml + self.ws[m.end():]

    def delete(self, rid):
        """delete a leaf region; if it is inline in a text block, also remove its anchor run"""
        host = self.host_block(rid)
        m = self.region(rid)
        self.ws = self.ws[:m.start()] + self.ws[m.end():]
        if host is not None:
            x = self._marked(host)
            mm = re.search(r'<Run%s%d%s[^>]*> </Run>' % (MK, rid, MK), x)
            assert mm, rid
            self._xaml[host] = x[:mm.start()] + x[mm.end():]

    def tag(self, rid):
        return re.search(r'<region region-id="%d"[^>]*>' % rid, self.ws).group(0)

    def attr(self, rid, name):
        m = re.search(r' %s="([-\d.]+)"' % name, self.tag(rid))
        return float(m.group(1)) if m else None

    def set_attr(self, rid, name, value):
        t = self.tag(rid)
        if (' %s="' % name) in t:
            t2 = re.sub(r' %s="[-\d.]+"' % name, ' %s="%r"' % (name, value), t, count=1)
        else:
            t2 = t[:-1] + ' %s="%r">' % (name, value)
        self.ws = self.ws.replace(t, t2, 1)

    def top_level(self):
        """[(rid, kind, top, actualHeight)] of regions placed on the page, in document order"""
        out, depth = [], 0
        for m in re.finditer(r'<region region-id="(\d+)"([^>]*)>(<\w+)|</region>', self.ws):
            if m.group(0) == '</region>':
                depth -= 1
                continue
            if depth == 0:   # regions nested in text blocks / solve blocks have their own local coordinates
                a = dict(re.findall(r' ([\w-]+)="([^"]*)"', m.group(2)))
                out.append((int(m.group(1)), m.group(3)[1:], float(a.get('top', 0)), float(a.get('actualHeight', 0))))
            depth += 1
        return out

    # -- editing formulas
    def set_define(self, rid, name, expr, eval_=None):
        """region becomes  name := expr  (eval_=True: 'name := expr = result', None: keep template choice)"""
        r = self.get(rid)
        has_eval = '<ml:eval>' in r if eval_ is None else eval_
        uo = re.search(r'<ml:unitOverride>.*?</ml:unitOverride>', r, re.S)
        uo = uo.group(0) if uo else '<ml:unitOverride><ml:placeholder /></ml:unitOverride>'
        body = ('<ml:eval>%s%s</ml:eval>' % (expr, uo)) if has_eval else expr
        r2, n = re.subn(r'<ml:define>.*</ml:define>', lambda _: '<ml:define>%s%s</ml:define>' % (ident(name), body), r, count=1, flags=re.S)
        assert n == 1, rid
        self.put(rid, r2)

    def set_eval(self, rid, expr):
        """region 'expr =' (keeps unit override)"""
        r = self.get(rid)
        r2, n = re.subn(r'<ml:eval>.*?(<ml:unitOverride>)', lambda m: '<ml:eval>' + expr + m.group(1), r, count=1, flags=re.S)
        assert n == 1, rid
        self.put(rid, r2)

    def set_math(self, rid, body):
        """replace the whole math content (keeps formattingOverride/resultFormat)"""
        r = self.get(rid)
        r2, n = re.subn(r'(<math[^>]*>).*?((?:<formattingOverride[^>]*/>|<resultFormat.*?</resultFormat>)*)</math>',
                        lambda m: m.group(1) + body + m.group(2) + '</math>', r, count=1, flags=re.S)
        assert n == 1, rid
        self.put(rid, r2)

    def set_value(self, rid, value):
        """change the first number of a 'name := 12 m' style definition"""
        r = self.get(rid)
        r2, n = re.subn(r'(<ml:define>.*?<ml:real>)[^<]*(</ml:real>)', lambda m: m.group(1) + str(value) + m.group(2), r, count=1, flags=re.S)
        assert n == 1, rid
        self.put(rid, r2)

    def find_define(self, name):
        """region id of the first definition of `name` (e.g. 'L_1')"""
        idx = re.escape(ident(name)).replace(re.escape('labels="VARIABLE" '), '(?:labels="\\w+" )?')
        for m in re.finditer(r'<region region-id="(\d+)"[^>]*><math[^>]*><ml:define>(?:<ml:function>)?' + idx, self.ws):
            return int(m.group(1))
        return None

    # -- text blocks
    def target(self, rid):
        """package path of the XamlPackage / image referenced by region rid"""
        m = re.search(r'<region region-id="%d"[^>]*>(?:(?!<region ).)*?item-idref="(\w+)"' % rid, self.ws, re.S)
        ref = m.group(1)
        return re.search(r'Target="/([^"]+)" Id="%s"' % ref, self.rels).group(1)

    def _block(self, rid):
        return re.search(r'(<region region-id="%d"[^>]*><text[^>]*>(?:<FlowDocument[^>]*/>)?<regions>)(.*?)(</regions></text>)' % rid, self.ws, re.S)

    def host_block(self, rid):
        """id of the text block that holds inline region rid, or None"""
        for m in re.finditer(r'<region region-id="(\d+)"[^>]*><text[^>]*>(?:<FlowDocument[^>]*/>)?<regions>(.*?)</regions></text>', self.ws, re.S):
            if re.search(r'<region region-id="%d"' % rid, m.group(2)):
                return int(m.group(1))
        return None

    def text(self, rid):
        """current XAML of text block rid (markers stripped)"""
        if rid in self._xaml:
            return re.sub(MK + r'\d+' + MK, '', self._xaml[rid])
        return _pkg_read(self.files[self.target(rid)])

    def _marked(self, rid):
        if rid not in self._xaml:
            x = _pkg_read(self.files[self.target(rid)])
            m = self._block(rid)
            if m:
                regs = [(int(a), int(c)) for a, c in re.findall(r'<region region-id="(\d+)"[^>]*text-caret-position="(\d+)"', m.group(2))]
                syms = symbols(x)
                ins = []
                for reg, c in regs:
                    k, v, off = syms[c + 1]
                    assert k == 'T' and v.startswith('<Run'), ('caret rule broken', rid, reg, v)
                    ins.append((off, reg))
                for off, reg in sorted(ins, reverse=True):
                    x = x[:off + 4] + '%s%d%s' % (MK, reg, MK) + x[off + 4:]
            self._xaml[rid] = x
        return self._xaml[rid]

    def replace_text(self, rid, old, new, count=1):
        """replace literal text inside a text block; asserts it occurs exactly `count` times"""
        x = self._marked(rid)
        assert x.count(old) == count, (rid, old, x.count(old))
        self._xaml[rid] = x.replace(old, new)

    def edit_xaml(self, rid, func):
        """func(marked_xaml) -> new marked_xaml ; keep the §id§ markers inside <Run tags"""
        self._xaml[rid] = func(self._marked(rid))

    def _commit_text(self, rid):
        x = self._xaml.pop(rid)
        car = {}
        for i, (k, v, off) in enumerate(symbols(x)):
            if k == 'T':
                for mm in re.finditer(MK + r'(\d+)' + MK, v):
                    car[int(mm.group(1))] = i - 1
        m = self._block(rid)
        if m:
            blk = m.group(2)
            regs = list(re.finditer(r'(<region region-id="(\d+)"[^>]*text-caret-position=")(\d+)(")', blk))
            assert sorted(car) == sorted(int(r.group(2)) for r in regs), ('inline regions vs anchors differ', rid)
            for rm in reversed(regs):
                blk = blk[:rm.start(3)] + str(car[int(rm.group(2))]) + blk[rm.end(3):]
            self.ws = self.ws[:m.start(2)] + blk + self.ws[m.end(2):]
        clean = re.sub(MK + r'\d+' + MK, '', x)
        t = self.target(rid)
        self.files[t] = _pkg_write(self.files[t], clean)

    def clone_inline(self, src_rid, where='after', anchor_rid=None, sep='<Run xml:lang="en-us">\t</Run>'):
        """copy inline region src_rid. where='after' (same line, after src), 'before' (before anchor_rid),
        'paragraph' (new paragraph after src's paragraph). Returns the new region id."""
        host = self.host_block(src_rid)
        assert host is not None, 'region %d is not inline' % src_rid
        x = self._marked(host)
        nid, nref = self._next_id, self._next_ref
        self._next_id += 1
        self._next_ref += 1
        rr = re.sub(r'region-id="\d+"', 'region-id="%d"' % nid, self.get(src_rid), count=1)
        rr = re.sub(r'resultRef="\d+"', 'resultRef="%d"' % nref, rr, count=1)
        anchor = anchor_rid if where == 'before' else src_rid
        a = self.region(anchor)
        pos = a.start() if where == 'before' else a.end()
        self.ws = self.ws[:pos] + rr + self.ws[pos:]
        tag = re.search(r'<Run%s%d%s[^>]*> </Run>' % (MK, anchor, MK), x)
        assert tag, anchor
        new_run = re.sub(MK + r'\d+' + MK, '%s%d%s' % (MK, nid, MK), tag.group(0))
        if where == 'after':
            x = x[:tag.end()] + sep + new_run + x[tag.end():]
        elif where == 'before':
            x = x[:tag.start()] + new_run + sep + x[tag.start():]
        else:
            ps = x.rfind('<Paragraph', 0, tag.start())
            pe = x.index('</Paragraph>', tag.end()) + len('</Paragraph>')
            para = x[ps:pe]
            plain = re.sub(r'<Run%s\d+%s' % (MK, MK), '<Run', para)
            para2 = plain.replace(re.sub(MK + r'\d+' + MK, '', tag.group(0)), new_run, 1)
            x = x[:pe] + para2 + x[pe:]
        self._xaml[host] = x
        return nid

    # -- pictures
    def replace_picture(self, rid, png_path, fit='box', width=None):
        """fit='box': keep the template box height, scale width, center in the old box (layout unchanged);
        fit='width': use `width` (or old width) and let height follow the image aspect."""
        pb = open(png_path, 'rb').read()
        w, h = struct.unpack('>II', pb[16:24])
        r0 = self.get(rid)
        W0, H0, L0 = self.attr(rid, 'width'), self.attr(rid, 'height'), self.attr(rid, 'left')
        if fit == 'box':
            dh, dw = H0, H0 * w / h
            if dw > W0:
                dw, dh = W0, W0 * h / w
            left = L0 + (W0 - dw) / 2
        else:
            dw = width or W0
            dh = dw * h / w
            left = (PAGE_W - dw) / 2
        r = r0
        for a_, v in ((' height=', dh), (' width=', dw), (' actualWidth=', dw), (' actualHeight=', dh),
                      ('display-width=', dw), ('display-height=', dh)):
            r, k = re.subn(a_ + r'"[\d.]+"', a_ + '"%r"' % v, r)
            assert k == 1, (rid, a_)
        self.put(rid, r)                     # replace first, then move (string snapshots!)
        self.set_attr(rid, 'left', left)
        self.files[self.target(rid)] = pb
        return dh - H0

    # -- layout
    def relayout(self, heights=None, fixed_first=1):
        """re-stack top-level regions keeping the original gaps between them.
        heights: {rid: real actualHeight measured after a Mathcad save}. Tops are snapped to GRID."""
        heights = heights or {}
        regs = self.top_level()
        new_top = [regs[0][2]]
        for (pr, _, ptop, ph), (nr, _, ntop, nh) in zip(regs, regs[1:]):
            gap = ntop - (ptop + ph)
            new_top.append(new_top[-1] + heights.get(pr, ph) + gap)
        for i, (rid, _, top, _) in enumerate(regs):
            if i >= fixed_first:
                self.set_attr(rid, 'top', round(new_top[i] / GRID) * GRID)
            if rid in heights:
                self.set_attr(rid, 'actualHeight', heights[rid])


# ----------------------------------------------------------------------------- readable dump
def readable(xml):
    t = re.sub(r'<ml:id[^>]*>(?:<Span[^>]*>)?([^<]*)(?:<pw:Subscript>([^<]*)</pw:Subscript></Span>)?</ml:id>',
               lambda m: m.group(1) + ('_' + m.group(2) if m.group(2) else '') + ' ', xml)
    t = re.sub(r'<ml:real>([^<]*)</ml:real>', r'\1 ', t)
    ops = {'plus': '+', 'minus': '-', 'mult': '*', 'div': '/', 'pow': '^', 'neg': 'NEG', 'scale': '', 'equal': '=='}
    t = re.sub(r'<ml:(\w+) />', lambda m: ops.get(m.group(1), m.group(1).upper()) + ' ', t)
    t = re.sub(r'<formattingOverride[^>]*/>|<resultFormat.*?</resultFormat>|<ml:unitOverride>.*?</ml:unitOverride>', '', t, flags=re.S)
    t = re.sub(r'</?(ml:apply|ml:parens|math|ml:define|ml:eval|ml:function|ml:boundVars|ml:sequence)[^>]*>',
               lambda m: {'<ml:define>': ' DEF[', '</ml:define>': ']', '<ml:eval>': ' EVAL[', '</ml:eval>': ']'}.get(m.group(0), ' '), t)
    return re.sub(r'\s+', ' ', t).strip()


def dump(path):
    doc = Mcdx.load(path)
    print('settings:', {k: v for k, v in doc.settings().items() if k in ('array-origin', 'automatic-recalculation')})
    for m in re.finditer(r'<region region-id="(\d+)"([^>]*)>(<math.*?</math>|<text[^>]*>|<picture.*?</picture>|<\w+)', doc.ws, re.S):
        a = dict(re.findall(r' (top|left|text-caret-position|actualWidth|actualHeight)="([\d.]+)"', m.group(2)))
        b = m.group(3)
        pos = ('top=%s h=%s' % (a['top'][:7], a.get('actualHeight', '')[:6])) if 'top' in a else ('caret=%s' % a.get('text-caret-position', ''))
        if b.startswith('<text'):
            print(m.group(1), 'TEXT', pos)
        elif b.startswith('<picture'):
            print(m.group(1), 'PICTURE', pos)
        elif b.startswith('<math'):
            print(m.group(1), pos, readable(b)[:300])
        else:
            print(m.group(1), b[1:].upper(), pos)


def texts(path):
    doc = Mcdx.load(path)
    for m in re.finditer(r'<region region-id="(\d+)"[^>]*><text', doc.ws):
        rid = int(m.group(1))
        x = doc.text(rid)
        paras = re.findall(r'<Paragraph[^>]*?(?:/>|>(.*?)</Paragraph>)', x, re.S)
        print('== text block', rid)
        for p in paras:
            print('   |', ''.join(re.findall(r'<Run[^>]*?(?:/>|>(.*?)</Run>)', p or '', re.S)).replace(' ', '·'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    cmd, path = sys.argv[1], sys.argv[2]
    if cmd == 'region':
        print(Mcdx.load(path).get(int(sys.argv[3])))
    else:
        {'dump': dump, 'texts': texts}[cmd](path)
