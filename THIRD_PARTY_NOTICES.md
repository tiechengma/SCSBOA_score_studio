# Third-party notices

This distribution includes unmodified open-source libraries and CPU OCR models. It does not bundle any user's scores or original documents. Retain the accompanying `licenses/` directory when redistributing the portable application.

- Qt for Python / PySide6 Essentials and Shiboken6 6.10.1: LGPL-3.0 option; dynamically linked Qt libraries remain in `_internal`. Source: https://code.qt.io/cgit/pyside/pyside-setup.git/ (tag v6.10.1). Qt base source: https://code.qt.io/cgit/qt/qtbase.git/ (tag v6.10.1). Corresponding source archives are available from https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.10.1-src/ and https://download.qt.io/official_releases/qt/6.10/6.10.1/submodules/ . No restriction is imposed on replacing/relinking these libraries, or reverse engineering for debugging modifications to the LGPL components.
- RapidOCR ONNX Runtime 1.4.4: Apache-2.0. https://github.com/RapidAI/RapidOCR . Bundled PaddleOCR detection/recognition/classification models are included in the wheel; upstream https://github.com/PaddlePaddle/PaddleOCR . No model download occurs during normal app use.
- ONNX Runtime: MIT. https://github.com/microsoft/onnxruntime
- OpenCV: Apache-2.0. https://github.com/opencv/opencv
- NumPy: BSD-3-Clause. https://github.com/numpy/numpy
- Pillow: HPND. https://github.com/python-pillow/Pillow
- pillow-heif / libheif: package notices copied below; libheif uses LGPL. https://github.com/bigcat88/pillow_heif and https://github.com/strukturag/libheif
- pdfplumber: MIT. https://github.com/jsvine/pdfplumber
- pdfminer.six: MIT. https://github.com/pdfminer/pdfminer.six
- pypdfium2 / PDFium: Apache-2.0 or BSD-3-Clause for bindings; PDFium and its dependencies have their own notices. https://github.com/pypdfium2-team/pypdfium2
- Python: PSF license. https://www.python.org/
- PyInstaller bootloader: GPL with distribution exception. https://pyinstaller.org/en/stable/license.html

Additional dependency copyright and license texts are copied from the installed distributions into `licenses/`. Exact build versions are in `requirements-lock.txt`. Consult the upstream notices for individual components; the applications' own files do not change those licenses.
