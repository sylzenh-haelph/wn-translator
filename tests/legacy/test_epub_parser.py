from parsers.epub_parser import parse_epub


document = parse_epub("input/test.epub")

print("Title:", document.title)
print("Author:", document.author)
print("Paragraphs:", len(document.paragraphs))

for paragraph in document.paragraphs:
    print()
    print("ID:", paragraph.id)
    print("TEXT:", paragraph.text)
    print("STYLE:", paragraph.style)

    for run in paragraph.runs:
        print("  RUN:", repr(run.text))
        print("  FORMAT:", run.formatting)
