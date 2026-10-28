# Browser edition — third-party notices

This web application distributes locally executed open-source libraries and an unmodified OCR recognition model. Runtime/model assets download to the browser; score files are processed locally.

- ONNX Runtime Web and Common 1.31.1 — MIT. https://github.com/microsoft/onnxruntime
- PDF.js / pdfjs-dist 6.4.299 — Apache-2.0. https://github.com/mozilla/pdf.js
- zip.js — BSD-3-Clause. https://github.com/gildas-lormeau/zip.js
- PaddleOCR PP-OCRv4 recognition model and character dictionary, distributed with RapidOCR ONNX Runtime 1.4.4 — Apache-2.0. https://github.com/PaddlePaddle/PaddleOCR and https://github.com/RapidAI/RapidOCR

Model preprocessing and CTC decoding are adapted from the Apache-2.0 RapidOCR/PaddleOCR implementation. Copyright 2020 PaddlePaddle Authors; RapidOCR contributors. Browser table parsing and application logic are part of Score Studio.

Exact dependency versions are in web/package-lock.json. License texts are included in the licenses/ directory beside this file. Vite and TypeScript are build-only tools. This application is not affiliated with or endorsed by SCSBOA or CompetitionSuite.
