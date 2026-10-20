from parsers.docx_parser import parse_docx
from reconstruction.docx_reconstructor import reconstruct_docx


source_path = "input/test.docx"
output_path = "output/test_reconstructed.docx"

document = parse_docx(source_path)

reconstruct_docx(
    document,
    output_path,
)

print("Reconstruction berhasil.")
print("Output:", output_path)
