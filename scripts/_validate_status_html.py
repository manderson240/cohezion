"""Throwaway HTML tag-balance validator for the status report."""
from html.parser import HTMLParser
import pathlib

p = pathlib.Path("docs/status/loop_status_2026-06-06.html")
html = p.read_text()
VOID = {"meta", "br", "img", "hr", "input", "link", "path", "rect", "circle",
        "polygon", "line", "marker", "tspan", "use", "stop"}
stack = []
errs = []


class C(HTMLParser):
    def handle_starttag(self, t, a):
        if t not in VOID:
            stack.append(t)

    def handle_endtag(self, t):
        if t in VOID:
            return
        if stack and stack[-1] == t:
            stack.pop()
        elif t in stack:
            popped = None
            while stack and popped != t:
                popped = stack.pop()
        else:
            errs.append("stray </%s>" % t)


C().feed(html)
print("size: %d bytes" % len(html))
print("unclosed at EOF: %s" % (stack[-5:] if stack else "none"))
print("stray closers: %s" % (errs[:5] if errs else "none"))
print("<svg>: %d  </svg>: %d" % (html.count("<svg"), html.count("</svg>")))
print("<table>: %d  </table>: %d" % (html.count("<table"), html.count("</table>")))
