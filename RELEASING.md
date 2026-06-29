# Releasing costgen to PyPI

Publishing is automated via GitHub Actions ([`.github/workflows/publish.yml`](.github/workflows/publish.yml))
using **PyPI Trusted Publishing (OIDC)** — no API token is stored in the repo.

## One-time setup (maintainer)

1. Create a [PyPI](https://pypi.org/) account (and verify email) if you don't have one.
2. Add a **pending trusted publisher** so the first release can create the project:
   - PyPI → *Your account* → **Publishing** → *Add a pending publisher*
   - **PyPI Project Name:** `costgen`
   - **Owner:** `yashdixit0885`
   - **Repository name:** `costgen`
   - **Workflow name:** `publish.yml`
   - **Environment:** *(leave blank)*
3. (Recommended) Do a dry run on **TestPyPI** first using the same flow.

## Cut a release

1. **Re-verify pricing** in `src/costgen/_pricing/data/*.json` against the providers'
   current pricing pages, and bump each record's `last_verified` date. Confirm the
   OpenAI numbers in particular (they're sourced from the public pricing page).
2. Bump `version` in `pyproject.toml` and add an entry to `CHANGELOG.md`.
3. Commit + merge to `main` (CI must be green).
4. Create the release — this triggers the publish workflow:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   gh release create v0.1.0 --title "costgen 0.1.0" --notes-file CHANGELOG.md
   ```
   (Or use the GitHub UI: *Releases → Draft a new release*.)
5. The workflow builds the sdist + wheel, runs `twine check`, and uploads to PyPI.
6. Verify:
   ```bash
   pip install "costgen[all]"
   python -c "import costgen; print(costgen.__version__)"
   ```
7. Update the README install section to lead with `pip install costgen`.

## Token fallback (if you don't use Trusted Publishing)

Create a PyPI API token, add it as a repo secret `PYPI_API_TOKEN`, and add this to
the publish step:

```yaml
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

Trusted Publishing is preferred — it avoids storing a long-lived secret.
