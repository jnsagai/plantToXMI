# EA Validation Template

Create a blank Sparx Enterprise Architect repository manually:

1. Open Enterprise Architect.
2. Create a new local project, preferably `.qea`.
3. Ensure the project contains at least one root model package.
4. Save it as `blank.qea` in this directory or another local path.
5. Run validation with:

```powershell
planttoxmi validate path\to\diagram.xmi --profile ea --ea-template tools\ea\blank.qea
```

Do not commit licensed, customer, or proprietary EA repositories.
