# Contributing to Awesome European OpenSource

⚠️ **Before contributing code to the European OpenSource project in any form including sending a pull request via GitHub, submitting a code fragment or patch via private email, or posting to public discussion groups you agree to release your code under the terms of the [Contributor License Agreement](CLA.md) and [CODE OF CONDUCT](https://github.com/european-opensource/europeanopensource.eu/blob/main/CODE_OF_CONDUCT.md).**

## How to Contribute

- **🚀 I want to submit a project**: [Open a GitHub Issue](https://github.com/European-OpenSource/awesome-european-opensource/issues/new?template=PROJECT_SUBMISSION.yml)
- **✏️ I want to update a project**: [Open an Issue](https://github.com/European-OpenSource/awesome-european-opensource/issues/new?template=PROJECT_UPDATE.yml)
- **🗑️ I want to remove a project**: [Open an Issue](https://github.com/European-OpenSource/awesome-european-opensource/issues/new?template=PROJECT_REMOVAL.yml)
- **❓ I have a question:** Ask in [Open an Issue](https://github.com/European-OpenSource/awesome-european-opensource/issues/new?template=QUESTION.yml)
- **🐛 I found a bug:** [Open an Issue](https://github.com/European-OpenSource/awesome-european-opensource/issues/new?template=BUG_REPORT.yml)
- **💡 I have an idea:** [Open an Issue](https://github.com/European-OpenSource/awesome-european-opensource/issues/new?template=FEATURE_REQUEST.yml)
- **💻 I want to code (or improve documentation):** See [Contributing code](#contributing-code) section

## Contributing Code

> ⚠️ **Important:** If you're looking to add a new feature, please check if a feature issue exists or create one before starting development.

When you've identified an issue and you want to work on it here's how you can get started:

1. Fork the repo
2. Setup project
   - If you using VS Code: Open the project in devcontainer mode
   - Or, setup your local env with `just setup`
3. Add your changes
4. Test your changes using `just test` to make sure everything still works
5. Commit & push your changes (we suggest use a feature or fix branch)
6. Open a PR to get your changes merged.

### With Dev Container (Recommended)

1. Requirements: `Docker >=24`
2. Open the project in Visual Studio Code
3. Install the Dev Containers extension
4. Reopen in container when prompted

### Without Dev Container

1. **Requirements**

   | pkg    | version  |
   | ------ | -------- |
   | Docker | `>=24`   |
   | Python | `>=3.12` |

2. **Check the project:**

   ```bash
   just setup
   ```

### PR Guidelines

- Keep PRs focused on a single feature/fix
- Include tests for new functionality
- Update documentation if needed
- Ensure all CI checks pass

### Code Style Guidelines

- Follow existing code patterns and conventions
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions small and focused
- Follow the project's ESLint configuration

### How to add a new project

The preferred way to submit a project is via GitHub Issue — the process is fully automated.

#### Via GitHub Issue (recommended)

1. [Open a submission issue](https://github.com/European-OpenSource/awesome-european-opensource/issues/new?template=PROJECT_SUBMISSION.yml) and fill in all the required fields.
2. A maintainer will add the `check-submission` label to trigger automated validation. The bot will post a comment with the result.
3. If validation passes, the maintainer adds the `approved-submission` label. The CI will automatically create a pull request with the project JSON file.
4. Once the PR is merged, the workflow [sync-europeanopensource-eu.yml](.github/workflows/sync-europeanopensource-eu.yml) syncs the data to [europeanopensource.eu](https://github.com/European-OpenSource/europeanopensource.eu).

#### Via Tally form (deprecated)

You can still submit a project via the [Tally form](https://europeanopensource.eu/form). Submissions received there are periodically reviewed by a maintainer, who will create a GitHub Issue on your behalf and run the same automated process described above. This path is less prioritised and takes longer to validate.

## Join our Community

[![LinkedIn](https://img.shields.io/badge/Linkedin-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/european-open-source)

#### [CODE OF CONDUCT](CODE_OF_CONDUCT.md)
