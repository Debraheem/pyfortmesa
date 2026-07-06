# Publishing the docs

The docs are built with MkDocs and published with GitHub Pages.

## One-Time GitHub Setup

In the GitHub repository:

1. Open `Settings`.
2. Open `Pages`.
3. Under `Build and deployment`, set `Source` to `GitHub Actions`.

After that, every push to `main` runs:

```text
.github/workflows/pages.yml
```

The workflow installs the docs requirements, runs:

```bash
python -m mkdocs build --strict --site-dir site
```

and deploys the generated `site/` directory to GitHub Pages.

## Site URL

The configured project Pages URL is:

```text
https://debraheem.github.io/pyfortmesa/
```

The first deploy can take a minute or two. If the page is not live yet, check
the `docs` workflow under the repository's `Actions` tab.

## Local Preview

From the repository root:

```bash
python -m pip install -r requirements-dev.txt
mkdocs serve
```

Then open:

```text
http://127.0.0.1:8000/pyfortmesa/
```
