| Aspect | Playwright | LaTeX | 
| :--- | :--- | :--- | 
| Template Rewrite | Zero. We use the exact same mgmtreporting.html file we have right now. All the work we've done on the template is preserved. | Complete. We would have to throw away the HTML file and create a new .tex file from scratch. All styling would need to be re-implemented using LaTeX commands. | 
| Dependencies | Medium. Requires pip install playwright and a one-time playwright install command. This is a self-contained, automated process. | Very High. Requires installing a massive, multi-gigabyte LaTeX distribution on your system (e.g., MacTeX). This is a heavy system-level dependency. |
| Styling & Layout | Easy. You continue to use Tailwind CSS and standard web technologies. The layout is visual and intuitive. | Difficult. The layout is controlled by complex and often non-intuitive commands. Simple things in CSS (like side-by-side divs) can be very complex in LaTeX. The learning curve is extremely steep. | 
| Data Integration | Easy. We are already doing this. We pass variables from Python to the Jinja2 template. This does not change at all. | More Complex. We would need to find a Python library (like pylatex) to programmatically generate the .tex file, which adds another layer of abstraction and potential for error. | 
| Final Output Quality | Very High. The PDF looks exactly like a modern web page. | Exceptional. The typography and document structure are often considered the gold standard, especially for text-heavy academic documents. |

---
| Aspect | weasyprint / playwright (Our Failed Approach) | fpdf2 (The New Approach) | 
| :--- | :--- | :--- | 
| How it Works | Converts a finished HTML document to PDF. | Builds a PDF from scratch using Python commands. | 
| Layout Control | Indirect and Unreliable. We are at the mercy of the converter's CSS engine. | Direct and Absolute. We have explicit control over every element's position, font, and page breaks. | 
| Dependencies | Complex and Fragile. Required Homebrew, Playwright downloads, and environment variables. | Simple and Robust. It is a pure Python library. pip install fpdf2 is all that is needed. | 
| Effort | We thought it would be low, but it became a high-effort series of failed tweaks. | The initial setup is a rewrite, but it is a structured, predictable programming task, not a guessing game of CSS rules. |

---
| Aspect | fpdf2 | LaTeX (with your expertise) | 
| :--- | :--- | :--- | 
| Layout Approach | Manual coordinate math. Very low-level. | Semantic document markup. High-level and powerful. | 
| Recreating the Design | Very Hard. The two-column layouts would be a nightmare of manual x, y positioning. | Achievable. You can use minipages or tcolorbox to create the side-by-side layouts and styled cards. It's what LaTeX is built for. | 
| Python Integration | Simple. pip install fpdf2 and call its Python functions. | Requires a wrapper library like PyLaTeX (which is excellent) to generate the .tex file programmatically. | 
| Dependencies | Minimal. Just a single pip install. | Heavy. Requires a full TeX distribution (MacTeX, TeX Live). However, as a LaTeX expert, you likely already have this installed. | 
| Final Output Quality | Good, but can look "programmatically generated." | Exceptional. Unmatched typographical quality. The gold standard for professional documents. |
---
| Aspect | PyLaTeX (Direct to LaTeX) | Markdown + Pandoc | 
| :--- | :--- | :--- | 
| Content Generation | Python code generates LaTeX commands. Can be verbose. | Python code generates simple Markdown. Very clean. | 
| Styling & Layout | Done entirely in Python using LaTeX commands. | Defined in a separate .latex template file. Excellent separation. | 
| Dependencies | pip install pylatex + LaTeX installation. | pip install pypandoc + Pandoc installation + LaTeX installation. | 
| Flexibility | Absolute, fine-grained control over everything. | High control via templates, but very complex layouts can be tricky. | 
| Maintainability | Can be hard to read/maintain if the layout is complex. | Excellent. The content (.md) and presentation (.latex) are separate. |

---
| Spalte 1 | Spalte 2 | Spalte 3 | Spalte 4 | Spalte 5           | Spalte 6 | Spalte 7 | Spalte 8 | 
| :------- | :------- | :------- | :------- | :----------------- | :------- | :------- | :------- | 
| ...      | ...      | ...      | ...      | ...                | ...      | ...      | ...      | 
|          |          |          |          | Unterhaltsaufwände |          |          | -1000    |
|          |          |          |          | Heizkosten         |          |          | -200     | 
|          |          |          |          | Strom              |          |          | -150     | 
|          |          |          |          | Aufwände           |          |          | -1350    | 
|          |          |          |          | Mieteinnahmen      |          |          | 5000     |
|          |          |          |          | Sonstiges          |          |          | 100      |
|          |          |          |          | Nettoergebnis      |          |          | 3750     |

---
| Spalte 5           | Spalte 8 | 
| :----------------- | :------- | 
| Mieteinnahmen      | 5000     | 
| Sonstiges          | 100      | 
| Aufwände           | 1350     | 
| Unterhaltsaufwände | 1000     | 
| Heizkosten         | 200      | 
| Strom              | 150      | 
| Nettoergebnis      | 3750     |