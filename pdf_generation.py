"""Deprecated root module.

This helper was moved into `vid2doc.pdf_generation`. Importing the root
module will raise an informative ImportError to guide developers to the
new path.
"""
raise ImportError("module 'pdf_generation' moved: import from 'vid2doc.pdf_generation' instead")
