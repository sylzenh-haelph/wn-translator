from parsers.docx_parser import parse_docx


document = parse_docx("input/test.docx")

print("Title:", document.title)
print("Paragraphs:", len(document.paragraphs))

for paragraph in document.paragraphs:
    print()
    print("ID:", paragraph.id)
    print("TEXT:", paragraph.text)

    for run in paragraph.runs:
        print("  RUN:", repr(run.text))
        print("  FORMAT:", run.formatting)
