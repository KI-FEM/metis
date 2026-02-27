import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
#    OcrMacOptions,
    PdfPipelineOptions,
#    RapidOcrOptions,
#    TesseractCliOcrOptions,
#    TesseractOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

if __name__ == "__main__":
    source_files = []
    output_folder = Path()
    output_files = []
    
    # ask for source path
    source_str = input(
        "Please provide the path to the PDF"
        " or a folder containing PDF files:\n(path): "
    )
    if not source_str:
        raise ValueError("No source provided.")
    p = Path(source_str)
    if not p.exists():
        raise ValueError("The provided source does not exist.")

    if p.is_dir():
        source_files = sorted(p.glob("*.pdf"))
    elif p.suffix == ".pdf":
        source_files = [p]
    else:
        raise ValueError("The provided source is not a PDF file.")
    
    data_path = Path(__file__).parent.parent.parent / "data"
    existing_folders = [p.name for p in data_path.iterdir() if p.is_dir()]
    input_prompt = "Please select the output directory from the following list:\n"
    for i, folder in enumerate(existing_folders):
        input_prompt += f"{i+1}: {folder}\n"
    input_prompt += "If you want to create a new folder, please provide the name.\n"
    input_prompt += "(number|name): "
        
    # ask for the output folder
    file_name = input(input_prompt)
    if not file_name:
        raise ValueError("No output provided.")
    if file_name.isdigit():
        index = int(file_name) - 1
        if 0 <= index < len(existing_folders):
            output_folder = data_path / existing_folders[index]
        else:
            raise ValueError(
                f"Invalid number for folder selection. (1 <= {index+1} <= "
                f"{len(existing_folders)}"
            )
    else:
        new_folder = data_path / file_name
        if not new_folder.exists():
            new_folder.mkdir(parents=True, exist_ok=True)
        output_folder = new_folder
            
    languages = ["en", "de"]
    input_prompt = "Please provide the language of the document:\n("
    input_prompt += "|".join(languages) + "): "
    
    # ask for language of document
    lang = input(input_prompt)
    if lang not in languages:
        raise ValueError(f"Invalid language: {lang}")
    lang_folder = output_folder / lang
    if not lang_folder.exists():
        lang_folder.mkdir(parents=True, exist_ok=True)
    output_folder = lang_folder
    
    # ask for module
    existing_modules = [p.name for p in output_folder.iterdir() if p.is_dir()]
    input_prompt = (
        "Please select the module name of the document from the following list:\n"
    )
    for i, folder in enumerate(existing_modules):
        input_prompt += f"{i+1}: {folder}\n"
    input_prompt += "If you want to create a new module, please provide the name.\n"
    input_prompt += "(number|name): "
    topic = input(input_prompt)
    if not topic:
        raise ValueError("No module provided.")
    if topic.isdigit():
        index = int(topic) - 1
        if 0 <= index < len(existing_modules):
            output_files = [(
                output_folder / existing_modules[index] / (source_file.stem + ".md")
            )
            for source_file in source_files]
        else:
            raise ValueError(
                f"Invalid number for module selection. (1 <= {index+1} <= "
                f"{len(existing_modules)}"
            )
    else:
        topic_folder = output_folder / topic
        if not topic_folder.exists():
            topic_folder.mkdir(parents=True, exist_ok=True)
        output_files = [
            topic_folder / (source_file.stem + ".md") for source_file in source_files
        ]
        
    # ask for OCR
    ocr = input("Do you want to (force) use OCR?\n(y/N): ")
    do_ocr = False
    if ocr.lower() == "y":
        do_ocr = True
    elif ocr.lower() != "n" and ocr.lower() != "":
        raise ValueError("Invalid input for OCR.")
    
    ocr_options = EasyOcrOptions(force_full_page_ocr=do_ocr, lang=[lang])
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_page_images = False
    pipeline_options.generate_picture_images = False
    pipeline_options.generate_table_images = False
    pipeline_options.do_ocr = do_ocr
    pipeline_options.ocr_options = ocr_options
    pipeline_options.do_table_structure = False
    pipeline_options.table_structure_options.do_cell_matching = False
    
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    print("The following files will be converted:")
    for source_file in source_files:
        print(f" - {source_file}")

    for source_file, output_file in zip(source_files, output_files):
        print(f"Converting document: {source_file}")
        start_time = time.time()

        # this could use convert_all,
        # but I decided against it to better see progress and avoid large memory usage
        result = converter.convert(source_file)

        print(f"Conversion successful. Exporting markdown to file: {str(output_file)}")

        md = result.document.export_to_markdown()
        with Path.open(output_file, "w") as f:
            f.write(md)
        end_time = time.time() - start_time
        print(f"Document converted and saved in {end_time:.2f} seconds.")