project = "Enclosure"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_external_toc",
]

source_suffix = {".md": "markdown"}
root_doc = "index"
external_toc_path = "_toc.yml"
external_toc_exclude_missing = True

autodoc_typehints = "description"
nitpicky = True

myst_enable_extensions = ["colon_fence", "deflist"]

exclude_patterns = ["_build"]
html_theme = "furo"
html_title = "Enclosure"
html_theme_options = {
    "source_repository": "https://github.com/szpak-dev/enclosure/",
    "source_branch": "main",
    "source_directory": "docs/",
}
